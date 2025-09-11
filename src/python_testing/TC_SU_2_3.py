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
from matter.clusters.Types import NullValue
from matter.interaction_model import Status
from matter.testing.event_attribute_reporting import EventSubscriptionHandler
from matter.testing.matter_testing import MatterBaseTest, TestStep, async_test_body, default_matter_test_main
from mobly import asserts

logger = logging.getLogger(__name__)


class OTAApplication:
    def __init__(self, app: str, name: str, node_id: int, discriminator: int = 1234, passcode: int = 20202021, secured_device_port: int = 5540, logs: bool = False, extra_args: list = None, log_file_path: str = None):
        self.app = app
        self.name = name
        self.node_id = node_id
        self.discriminator = discriminator
        self.passcode = passcode
        self.secured_device_port = secured_device_port
        self.logs = logs
        self.extra_args = extra_args or []
        self.log_file_path = log_file_path or f'/tmp/{self.name}_output.log'
        self.process = None
        self.log_thread = None

    async def launch(self):
        command = self.get_command()
        if not os.path.exists(self.app):
            logger.error(f'{self.name}: binary not found at {self.app}')
        elif not os.access(self.app, os.X_OK):
            logger.error(f'{self.name}: binary is not executable: {self.app}')

        logger.info(f'Launching {self.name} with command: {" ".join(command)}')
        try:
            with open(self.log_file_path, 'a') as f:
                f.write(f'\n==== {self.name} launch at {time.time():.0f} ====' '\n')
        except Exception as e:
            logger.warning(f'{self.name}: could not open log file {self.log_file_path}: {e}')

        self.process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        asserts.assert_true(self.process is not None, f'Failed to launch {self.name}')

        logger.info(f'{self.name} started with PID {self.process.pid}, port {self.secured_device_port}, logs -> {self.log_file_path}')

        if self.logs:
            self.start_log_thread()

        await asyncio.sleep(10)

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

    def _follow_output(self):
        for line in self.process.stdout:
            with open(self.log_file_path, "a") as f:
                f.write(line)
                f.flush()

    def start_log_thread(self):
        self.log_thread = threading.Thread(target=self._follow_output, daemon=True)
        self.log_thread.start()

    async def commission(self, controller):
        logger.info(f"Commissioning {self.name} with discriminator {self.discriminator} and passcode {self.passcode}")
        resp = await controller.CommissionOnNetwork(
            nodeId=self.node_id,
            setupPinCode=self.passcode,
            filterType=ChipDeviceCtrl.DiscoveryFilterType.LONG_DISCRIMINATOR,
            filter=self.discriminator
        )
        logger.info(f"{self.name} commissioned: {resp}")
        return resp


class OTAProvider(OTAApplication):
    def __init__(self, app: str, name: str, filepath: str, node_id: int, discriminator: int = 1234, passcode: int = 20202021, secured_device_port: int = 5540, logs: bool = False, extra_args: list = None, log_file_path: str = None):
        self.filepath = filepath
        super().__init__(app, name, node_id, discriminator, passcode, secured_device_port, logs, extra_args or [], log_file_path)

    def get_command(self):
        # Provider CLI: ./out/debug/chip-ota-provider-app --filepath firmware_v2.ota --discriminator 1234 --passcode 20202021 --secured-device-port 5540 [extra_args]
        cmd = [self.app,
               '--filepath', self.filepath,
               '--discriminator', str(self.discriminator),
               '--passcode', str(self.passcode),
               '--secured-device-port', str(self.secured_device_port)]
        cmd += self.extra_args
        logger.info(f'{self.name} command: {" ".join(cmd)}')
        return cmd


class OTARequestor(OTAApplication):
    def __init__(self, app: str, name: str, node_id: int, discriminator: int = 1234, passcode: int = 20202021, secured_device_port: int = 5541, logs: bool = False, extra_args: list = None, log_file_path: str = None):
        super().__init__(app, name, node_id, discriminator, passcode, secured_device_port, logs, extra_args, log_file_path)

    def get_command(self):
        # Requestor CLI: ./out/debug/chip-ota-requestor-app --discriminator 1234 --passcode 20202021 --secured-device-port 5541 --autoApplyImage --KVS /tmp/chip_kvs_requestor [extra_args]
        cmd = [self.app,
               '--discriminator', str(self.discriminator),
               '--passcode', str(self.passcode),
               '--secured-device-port', str(self.secured_device_port),
               '--autoApplyImage',
               '--KVS', f'/tmp/chip_kvs_requestor']
        cmd += self.extra_args
        logger.info(f'{self.name} command: {" ".join(cmd)}')
        return cmd


class TC_SU_2_3(MatterBaseTest):
    """
    This test case verifies that the DUT behaves according to the spec when it is transferring images from the TH/OTA-P.
    """

    cluster_otap = Clusters.OtaSoftwareUpdateProvider
    cluster_otar = Clusters.OtaSoftwareUpdateRequestor

    # TH variables
    PROVIDER_NODE_ID = 10
    PROVIDER_PORT = 5540
    REQUESTOR_PORT = 5541

    provider = None

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

    async def _write_acl_rules(self, controller, endpoint: int, node_id):
        logger.info("Configure ACL Entries")
        admin_node_id = controller.nodeId
        logger.info(f"Admin node id is {admin_node_id}")
        logger.info(f"FabricId value: {controller.fabricId}")

        acl_attr_base = await self.read_single_attribute_check_success(
            dev_ctrl=controller,
            cluster=Clusters.AccessControl,
            attribute=Clusters.AccessControl.Attributes.Acl,
            node_id=node_id,
        )
        logger.info(f"Provider base acl {acl_attr_base}")

        acl_entries = [
            Clusters.Objects.AccessControl.Structs.AccessControlEntryStruct(
                fabricIndex=controller.fabricId,
                privilege=Clusters.AccessControl.Enums.AccessControlEntryPrivilegeEnum.kAdminister,
                authMode=Clusters.AccessControl.Enums.AccessControlEntryAuthModeEnum.kCase,
                subjects=[admin_node_id],
                targets=NullValue
            ),
            Clusters.Objects.AccessControl.Structs.AccessControlEntryStruct(
                fabricIndex=controller.fabricId,
                privilege=Clusters.AccessControl.Enums.AccessControlEntryPrivilegeEnum.kOperate,
                authMode=Clusters.AccessControl.Enums.AccessControlEntryAuthModeEnum.kCase,
                subjects=[],
                targets=[Clusters.AccessControl.Structs.AccessControlTargetStruct(
                    endpoint=NullValue,
                    cluster=self.cluster_otap.id,
                    deviceType=NullValue
                )]
            )
        ]

        all_acls = acl_attr_base + acl_entries
        acl_attr = Clusters.Objects.AccessControl.Attributes.Acl(value=all_acls)
        resp = await controller.WriteAttribute(node_id, [(endpoint, acl_attr)])
        asserts.assert_equal(resp[0].Status, Status.Success, "ACL write failed.")
        logger.info("ACL permissions configured successfully.")

    async def _write_ota_providers(self, controller, provider_node_id, requestor_node_id, endpoint: int = 0):
        current_otap_info = await self.read_single_attribute_check_success(
            dev_ctrl=controller,
            cluster=self.cluster_otar,
            attribute=self.cluster_otar.Attributes.DefaultOTAProviders,
            node_id=requestor_node_id,
        )
        logger.info(f"OTA Providers: {current_otap_info}")

        # Create Provider Location into Requestor
        provider_location_struct = self.cluster_otar.Structs.ProviderLocation(
            providerNodeID=provider_node_id,
            endpoint=endpoint,
            fabricIndex=controller.fabricId
        )

        # Create the OTA Provider Attribute
        ota_providers_attr = self.cluster_otar.Attributes.DefaultOTAProviders(value=[provider_location_struct])

        # Write the Attribute
        resp = await controller.WriteAttribute(
            attributes=[(endpoint, ota_providers_attr)],
            nodeid=requestor_node_id,
        )
        asserts.assert_equal(resp[0].Status, Status.Success, "Failed to write Default OTA Providers Attribute")
        logger.info("OTA Providers configured successfully.")

    async def _announce_ota_provider(self, controller, provider_node_id, requestor_node_id, reason: Clusters.OtaSoftwareUpdateRequestor.Enums.AnnouncementReasonEnum = Clusters.OtaSoftwareUpdateRequestor.Enums.AnnouncementReasonEnum.kUpdateAvailable):
        cmd_announce_ota_provider = self.cluster_otar.Commands.AnnounceOTAProvider(
            providerNodeID=provider_node_id,
            vendorID=0xFFF1,
            announcementReason=reason,
            metadataForNode=None,
            endpoint=0
        )
        logger.info("Sending AnnounceOTA Provider Command")
        cmd_resp = await self.send_single_cmd(
            cmd=cmd_announce_ota_provider,
            dev_ctrl=controller,
            node_id=requestor_node_id,
            endpoint=0,
        )
        logger.info(f"Announce command sent {cmd_resp}")
        return cmd_resp

    @async_test_body
    async def teardown_test(self):
        if hasattr(self, 'provider') and self.provider is not None:
            logger.info("Terminating provider in teardown_test")
            await self.provider.terminate()
            self.provider = None

    @async_test_body
    async def test_TC_SU_2_3(self):
        # Initialize provider variable
        self.provider = None

        th = self.default_controller
        endpoint = self.get_endpoint(default=0)

        # Get setup payload info to extract discriminator and passcode
        setup_payloads = self.get_setup_payload_info()
        discriminator = setup_payloads[0].filter_value if setup_payloads else (
            self.matter_test_config.discriminators[0] if self.matter_test_config.discriminators else 1234
        )
        passcode = setup_payloads[0].passcode if setup_payloads else 20202021

        # Precondition: DUT is commissioned
        self.step("precondition")

        # Verify that the DUT obtains the User Consent from the user prior to transfer of software update image. This step is vendor specific.
        self.step(1)

        self.provider = OTAProvider(
            app='./out/debug/chip-ota-provider-app',
            name='provider_1',
            node_id=self.PROVIDER_NODE_ID,
            filepath='firmware_requestor_v2.ota',
            discriminator=discriminator,
            passcode=passcode,
            secured_device_port=self.PROVIDER_PORT,
            logs=True,
            extra_args=["-u", "deferred", "-c"],
        )
        await self.provider.launch()
        await self.provider.commission(th)

        # Configure ACL rules on the provider
        await self._write_acl_rules(controller=th, endpoint=0, node_id=self.PROVIDER_NODE_ID)

        # Configure OTA providers on the requestor (DUT)
        await self._write_ota_providers(controller=th, provider_node_id=self.PROVIDER_NODE_ID, requestor_node_id=self.dut_node_id, endpoint=0)

        # Create event subscriber for StateTransition events
        state_transition_event_handler = EventSubscriptionHandler(
            expected_cluster=self.cluster_otar,
            expected_event_id=self.cluster_otar.Events.StateTransition.event_id
        )
        await state_transition_event_handler.start(th, self.dut_node_id, endpoint=0, min_interval_sec=0, max_interval_sec=60*6)

        # Announce OTA provider to trigger the process
        await self._announce_ota_provider(th, self.PROVIDER_NODE_ID, self.dut_node_id)

        # Wait for transition to Querying state
        event_report = state_transition_event_handler.wait_for_event_report(
            self.cluster_otar.Events.StateTransition, timeout_sec=30)
        logger.info(f"Event report - transition to Querying: {event_report}")
        asserts.assert_equal(event_report.previousState, self.cluster_otar.Enums.UpdateStateEnum.kIdle,
                             "Previous state was not Idle")
        asserts.assert_equal(event_report.newState, self.cluster_otar.Enums.UpdateStateEnum.kQuerying, "New state is not Querying")

        # Wait for transition to DelayedOnUserConsent state
        event_report = state_transition_event_handler.wait_for_event_report(
            self.cluster_otar.Events.StateTransition, timeout_sec=30)
        logger.info(f"Event report - transition to DelayedOnUserConsent: {event_report}")
        asserts.assert_equal(event_report.previousState, self.cluster_otar.Enums.UpdateStateEnum.kQuerying,
                             "Previous state was not Querying")
        asserts.assert_equal(event_report.newState, self.cluster_otar.Enums.UpdateStateEnum.kDelayedOnUserConsent,
                             "New state is not DelayedOnUserConsent")

        logger.info("Step 1 PASSED: DUT correctly transitioned to DelayedOnUserConsent state, indicating it requested user consent before proceeding with the software update")

        # Clean up event handler
        state_transition_event_handler.reset()

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
