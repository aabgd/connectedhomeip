#
#    Copyright (c) 2023 Project CHIP Authors
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

# === BEGIN CI TEST ARGUMENTS ===
# test-runner-runs:
#   run1:
#     app: ${ALL_CLUSTERS_APP}
#     app-args: --discriminator 1234 --KVS kvs1 --trace-to json:${TRACE_APP}.json
#     script-args: >
#       --storage-path admin_storage.json
#       --commissioning-method on-network
#       --discriminator 1234
#       --passcode 20202021
#       --trace-to json:${TRACE_TEST_JSON}.json
#       --trace-to perfetto:${TRACE_TEST_PERFETTO}.perfetto
#     factory-reset: true
#     quiet: true
# === END CI TEST ARGUMENTS ===

import logging

import chip.clusters as Clusters
from chip.testing.matter_testing import MatterBaseTest, TestStep, async_test_body, default_matter_test_main
from mobly import asserts


class TC_BOOL_2_2(MatterBaseTest):

    def desc_TC_BOOL_2_2(self) -> str:
        return "[TC-BOOL-2.2] Primary Functionality with Server as DUT"

    def steps_TC_BOOL_2_2(self) -> list[TestStep]:
        steps = [
            TestStep("1", "Commission DUT to TH done", is_commissioning=True),
            TestStep("2a", "Bring the DUT into a state so StateValue is FALSE."),
            TestStep("2b", "TH reads the StateValue attribute from the DUT."),
            TestStep("3a", "Bring the DUT into a state so StateValue is TRUE."),
            TestStep("3b", "TH reads the StateValue attribute from the DUT."),
            TestStep("4a", "Set up subscription to StateChange event."),
            TestStep("4b", "Bring the DUT into a state so StateValue is FALSE."),
            TestStep("4c", "TH reads the StateValue attribute from the DUT."),
            TestStep("4d", "Bring the DUT into a state so StateValue is TRUE."),
            TestStep("4e", "TH reads the StateValue attribute from the DUT."),
        ]
        return steps

    # def pics_TC_BOOLCFG_2_1(self) -> list[str]:
    #     pics = [
    #         "BOOLCFG.S",
    #     ]
    #     return pics

    @async_test_body
    async def test_TC_BOOL_2_2(self):

        # Commission DUT to TH done
        self.step("1")

        # Bring the DUT into a state so StateValue is FALSE.
        self.step("2a")

        # TH reads the StateValue attribute from the DUT.
        self.step("2b")

        # Verify that value in the response is FALSE.

        # Bring the DUT into a state so StateValue is TRUE.
        self.step("3a")

        # TH reads the StateValue attribute from the DUT.
        self.step("3b")

        # Verify that value in the response is TRUE.

        # Set up subscription to StateChange event.
        self.step("4a")

        # Bring the DUT into a state so StateValue is FALSE.
        self.step("4b")

        # Receive StateChange event with StateValue set to FALSE.

        # TH reads the StateValue attribute from the DUT.
        self.step("4c")

        # Verify that value in the response is FALSE.

        # Bring the DUT into a state so StateValue is TRUE.
        self.step("4d")

        # Receive StateChange event with StateValue set to TRUE.

        # TH reads the StateValue attribute from the DUT.
        self.step("4e")

        # Verify that value in the response is TRUE.


if __name__ == "__main__":
    default_matter_test_main()
