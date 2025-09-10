#
#    Copyright (c) 2025 Project CHIP Authors
#    All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#

# See https://github.com/project-chip/connectedhomeip/blob/master/docs/testing/python.md#defining-the-ci-test-arguments
# for details about the block below.
#
# === BEGIN CI TEST ARGUMENTS ===
# test-runner-runs:
#   run1:
#     app: ${OTA_REQUESTOR_APP}
#     app-args: >
#       --discriminator 1234
#       --passcode 20202021
#       --secured-device-port 5541
#       --KVS /tmp/chip_kvs_requestor
#       --trace-to json:${TRACE_APP}.json
#     script-args: >
#       --storage-path admin_storage.json
#       --commissioning-method on-network
#       --discriminator 1234
#       --passcode 20202021
#       --vendor-id 65521
#       --product-id 32769
#       --endpoint 0
#       --trace-to json:${TRACE_TEST_JSON}.json
#       --trace-to perfetto:${TRACE_TEST_PERFETTO}.perfetto
#     factory-reset: true
#     quiet: true
# === END CI TEST ARGUMENTS ===

import logging
import shlex
import subprocess
import threading
import time
import os
import asyncio

import matter.clusters as Clusters
from matter import ChipDeviceCtrl
from matter.testing.matter_testing import MatterBaseTest, TestStep, async_test_body, default_matter_test_main
from mobly import asserts

logger = logging.getLogger(__name__)


class OTAProvider():
    def __init__(self, app: str, name: str, filepath: str, node_id: int, discriminator: int = 1234, passcode: int = 20202021, secured_device_port: int = 5540, logs: bool = False):
        self.app = app
        self.name = name
        self.filepath = filepath
        self.node_id = node_id
        self.discriminator = discriminator
        self.passcode = passcode
        self.secured_device_port = secured_device_port
        self.logs = logs
        self.log_file_path = f'/tmp/{self.name}_output.log'
        self.process = None
        self.log_thread = None

    async def launch(self):
        command = self.get_command()
        # Basic sanity about binary
        if not os.path.exists(self.app):
            logger.error(f'{self.name}: binary not found at {self.app}')
        elif not os.access(self.app, os.X_OK):
            logger.error(f'{self.name}: binary is not executable: {self.app}')

        logger.info(f'Launching {self.name} with command: {command}')
        # Open a header in the log file early for easier correlation
        try:
            with open(self.log_file_path, 'a') as f:
                f.write(f'\n==== {self.name} launch at {time.time():.0f} ====' '\n')
        except Exception as e:
            logger.warning(f'{self.name}: could not open log file {self.log_file_path}: {e}')

        self.process = subprocess.Popen(
            shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        asserts.assert_true(self.process is not None, f'Failed to launch {self.name}')

        logger.info(f'{self.name} started with PID {self.process.pid}, port {self.secured_device_port}, logs -> {self.log_file_path}')

        if self.logs:
            self.start_log_thread()

        # Give the process some time to bind sockets and print status
        await asyncio.sleep(5)

        # If process died early, dump output to help debugging
        if self.process.poll() is not None:
            try:
                remaining = self.process.stdout.read() if self.process.stdout else ''
            except Exception:
                remaining = ''
            logger.error(f'{self.name} exited early with code {self.process.returncode}. Output tail:\n{remaining[-2000:]}')
            asserts.fail(f'{self.name} terminated prematurely (rc={self.process.returncode})')

    async def terminate(self):
        if self.process:
            logger.info(f'{self.name}: terminating PID {self.process.pid}')
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired as e:
                self.process.kill()
                logger.error(f'Error terminating process: {e}')
            logger.info(f'{self.name}: process terminated with rc={self.process.returncode}')

    # Thread that write logs without block test
    def _follow_output(self):
        for line in self.process.stdout:
            with open(self.log_file_path, "a") as f:
                f.write(line)
                f.flush()

    def start_log_thread(self):
        self.log_thread = threading.Thread(target=self._follow_output, daemon=True)
        self.log_thread.start()

    def get_command(self):
        return f'{self.app} --filepath {self.filepath} --discriminator {self.discriminator} --passcode {self.passcode} --secured-device-port {self.secured_device_port}'

    async def commission(self, controller):
        """
        Commission this OTA provider using the given controller.
        """
        logger.info(f"Commissioning {self.name} with discriminator {self.discriminator} and passcode {self.passcode}")
        resp = await controller.CommissionOnNetwork(
            nodeId=self.node_id,
            setupPinCode=self.passcode,
            filterType=ChipDeviceCtrl.DiscoveryFilterType.LONG_DISCRIMINATOR,
            filter=self.discriminator
        )
        logger.info(f"{self.name} commissioned: {resp}")
        return resp


class TC_SU_2_3(MatterBaseTest):
    """
    This test case verifies that the DUT behaves according to the spec when it is transferring images from the TH/OTA-P.
    """

    cluster_otap = Clusters.OtaSoftwareUpdateProvider
    cluster_otar = Clusters.OtaSoftwareUpdateRequestor

    provider_process = None

    # TH variables
    P1_NODE_ID = 10
    P2_NODE_ID = 11

    def desc_TC_SU_2_3(self):
        return '[TC-SU-2.3] Transfer of Software Update Images between DUT and TH/OTA-P'

    def pics_TC_SU_2_3(self):
        """Return the PICS definitions associated with this test."""
        pics = [
            'MCORE.OTA.Requestor',
        ]
        return pics

    def steps_TC_SU_2_3(self):
        return [TestStep("precondition", "TH is commissioned", is_commissioning=True),
                TestStep(1, 'DUT sends a QueryImage command to the TH/OTA-P. RequestorCanConsent is set to True by DUT. OTA-P/TH responds with a QueryImageResponse with UserConsentNeeded field set to True.',
                         'Verify that the DUT obtains the User Consent from the user prior to transfer of software update image. This step is vendor specific.'),
                TestStep(2, 'DUT sends a QueryImage command to the TH/OTA-P. TH/OTA-P sends a QueryImageResponse back to DUT. QueryStatus is set to "UpdateAvailable". Set ImageURI to the location where the image is located.',
                         'Verify that there is a transfer of the software image from the TH/OTA-P to the DUT.'
                         'Verify that the Maximum Block Size requested by DUT should be'
                         '- no larger than 8192 (2^13) bytes over TCP transport.'
                         '- no larger than 1024 (2^10) bytes over non-TCP transports.'),
                TestStep(3, 'DUT sends a QueryImage command to the TH/OTA-P. TH/OTA-P sends a QueryImageResponse back to DUT. QueryStatus is set to "UpdateAvailable". Set ImageURI with the https url of the software image.',
                         'Verify that there is a transfer of the software image from the TH/OTA-P to the DUT from the https url and not from the OTA-P.'),
                TestStep(4, 'During the transfer of the image to the DUT, force fail the transfer before it completely transfers the image. Wait for the Idle timeout so that reading the UpdateState Attribute of the OTA Requestor returns the value as Idle. Initiate another QueryImage Command from DUT to the TH/OTA-P.',
                         'Verify that the BDX Idle timeout should be no less than 5 minutes.'
                         'Verify that the DUT starts a new transfer of software image when sending another QueryImage request.'),
                TestStep(5, 'During the transfer of the image to the DUT, force fail the transfer before it completely transfers the image. Initiate another QueryImage Command from DUT to the TH/OTA-P. Set the RC[STARTOFS] bit and associated STARTOFS field in the ReceiveInit Message to indicate the resumption of a transfer previously aborted.',
                         'Verify that the DUT starts receiving the rest of the software image after resuming the image transfer.')
                ]

    @async_test_body
    async def test_TC_SU_2_3(self):
        # Precondition: DUT is commissioned
        self.step("precondition")

        th = self.default_controller
        endpoint = self.get_endpoint(default=0)

        # Get setup payload info to extract discriminator and passcode
        setup_payloads = self.get_setup_payload_info()
        discriminator = setup_payloads[0].filter_value if setup_payloads else (
            self.matter_test_config.discriminators[0] if self.matter_test_config.discriminators else 1234
        )
        passcode = setup_payloads[0].passcode if setup_payloads else 20202021

        # DUT sends a QueryImage command to the TH/OTA-P.
        # RequestorCanConsent is set to True by DUT.
        # OTA-P/TH responds with a QueryImageResponse with UserConsentNeeded field set to True.
        self.step(1)

        provider_1 = OTAProvider(app='./out/debug/chip-ota-provider-app',
                                 name='provider_1',
                                 node_id=self.P1_NODE_ID,
                                 filepath='firmware_requestor_v2.ota',
                                 discriminator=discriminator,
                                 passcode=passcode,
                                 logs=True)
        await provider_1.launch()
        await provider_1.commission(th)

        await provider_1.terminate()

        # Verify that the DUT obtains the User Consent from the user prior to transfer of software update image. This step is vendor specific.

        # DUT sends a QueryImage command to the TH/OTA-P.
        # TH/OTA-P sends a QueryImageResponse back to DUT.
        # QueryStatus is set to "UpdateAvailable".
        # Set ImageURI to the location where the image is located.
        self.step(2)

        # Verify that there is a transfer of the software image from the TH/OTA-P to the DUT.

        # Verify that the Maximum Block Size requested by DUT should be
        # - no larger than 8192 (2^13) bytes over TCP transport.
        # - no larger than 1024 (2^10) bytes over non-TCP transports.

        # DUT sends a QueryImage command to the TH/OTA-P.
        # TH/OTA-P sends a QueryImageResponse back to DUT.
        # QueryStatus is set to "UpdateAvailable".
        # Set ImageURI with the https url of the software image.
        # HTTPS Transfer not available, skip test
        self.skip_step(3)

        # Verify that there is a transfer of the software image from the TH/OTA-P to the DUT from the https url and not from the OTA-P.

        # During the transfer of the image to the DUT, force fail the transfer before it completely transfers the image.
        # Wait for the Idle timeout so that reading the UpdateState Attribute of the OTA Requestor returns the value as Idle.
        # Initiate another QueryImage Command from DUT to the TH/OTA-P.
        self.step(4)

        # Verify that the BDX Idle timeout should be no less than 5 minutes.

        # Verify that the DUT starts a new transfer of software image when sending another QueryImage request.

        # During the transfer of the image to the DUT, force fail the transfer before it completely transfers the image.
        # Initiate another QueryImage Command from DUT to the TH/OTA-P.
        # Set the RC[STARTOFS] bit and associated STARTOFS field in the ReceiveInit Message to indicate the resumption of a transfer previously aborted.
        self.step(5)


if __name__ == "__main__":
    default_matter_test_main()
