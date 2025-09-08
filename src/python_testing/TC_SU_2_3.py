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

import matter.clusters as Clusters
from matter.testing.matter_testing import MatterBaseTest, TestStep, async_test_body, default_matter_test_main
from mobly import asserts

logger = logging.getLogger(__name__)


class App():
    def __init__(self, app: str, name: str, discriminator: int, passcode: int, secured_device_port: int):
        self.app = app
        self.name = name
        self.discriminator = discriminator
        self.passcode = passcode
        self.secured_device_port = secured_device_port
        self.log_file_path = f'/tmp/{self.name}_output.log'
        self.process = None
        self.log_thread = None

    def launch(self):
        command = self.get_command()
        logger.info(f'Launching {self.name} with command: {command}')
        self.process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.start_log_thread()
        time.sleep(5)

    def terminate(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired as e:
                self.process.kill()
                logger.error(f'Error terminating process: {e}')
            logger.info('Process terminated')

    # Thread that write logs without block test
    def _follow_output(self):
        for line in self.process.stdout:
            with open(self.log_file_path, "a") as f:
                f.write(line)
                f.flush()

    def start_log_thread(self):
        self.log_thread = threading.Thread(target=self._follow_output, daemon=True)
        self.log_thread.start()


class Provider(App):
    def __init__(self, app: str, name: str, filepath: str, discriminator: int = 1234, passcode: int = 20202021, secured_device_port: int = 5540):
        super().__init__(app, name, discriminator, passcode, secured_device_port)
        self.filepath = filepath

    def get_command(self):
        return f'{self.app} --filepath {self.filepath} --discriminator {self.discriminator} --passcode {self.passcode} --secured-device-port {self.secured_device_port}'


class Requestor(App):
    def __init__(self, app: str, name: str, kvs: str, discriminator: int = 1234, passcode: int = 20202021, secured_device_port: int = 5541):
        super().__init__(app, name, discriminator, passcode, secured_device_port)
        self.kvs = kvs

    def get_command(self):
        return f'{self.app} --discriminator {self.discriminator} --passcode {self.passcode} --secured-device-port {self.secured_device_port} --autoApplyImage --KVS {self.kvs}'


class TC_SU_2_3(MatterBaseTest):
    """
    This test case verifies that the DUT behaves according to the spec when it is transferring images from the TH/OTA-P.
    """

    cluster_otap = Clusters.OtaSoftwareUpdateProvider
    cluster_otar = Clusters.OtaSoftwareUpdateRequestor

    provider_1 = Provider(app='./out/debug/chip-ota-provider-app', name='provider_1',
                          filepath='firmware_requestor_v2.ota')
    requestor_1 = Requestor(app='./out/debug/chip-ota-requestor-app', name='requestor_1',
                            kvs='/tmp/chip_kvs_requestor')
    provider_process = None
    requestor_process = None

    def setup_class(self):
        logger.info("Setting up TC_SU_2_3 class resources")
        # Launch the OTA Provider
        self.provider_process = self.provider_1.launch()
        self.requestor_process = self.requestor_1.launch()

    def teardown_class(self):
        logger.info("Tearing down TC_SU_2_3 class resources")
        # Terminate the OTA Provider
        self.provider_1.terminate()
        self.requestor_1.terminate()

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

        # DUT sends a QueryImage command to the TH/OTA-P.
        # RequestorCanConsent is set to True by DUT.
        # OTA-P/TH responds with a QueryImageResponse with UserConsentNeeded field set to True.
        self.step(1)

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
