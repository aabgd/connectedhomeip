#
#    Copyright (c) 2024 Project CHIP Authors
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

# See https://github.com/project-chip/connectedhomeip/blob/master/docs/testing/python.md#defining-the-ci-test-arguments
# for details about the block below.
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
#       --endpoint 1
#       --trace-to json:${TRACE_TEST_JSON}.json
#       --trace-to perfetto:${TRACE_TEST_PERFETTO}.perfetto
#     factory-reset: true
#     quiet: true
# === END CI TEST ARGUMENTS ===

import copy
import logging
import random
from collections import namedtuple

import chip.clusters as Clusters
from chip import ChipDeviceCtrl  # Needed before chip.FabricAdmin
from chip.clusters import Globals
from chip.clusters.Types import NullValue
from chip.interaction_model import InteractionModelError, Status
from chip.testing.matter_testing import MatterBaseTest, TestStep, async_test_body, default_matter_test_main
from mobly import asserts

logger = logging.getLogger(__name__)


# corrio contra linux-x64-thermostat-no-ble y contra linux-x64-all-clusters-no-ble
# no asi el yaml Test_TC_TSTAT_2_2.yaml que solo corrio contra thermostat
class TC_TSTAT_2_2(MatterBaseTest):

    def desc_TC_TSTAT_2_2(self) -> str:
        """Returns a description of this test"""
        return "3.1.2. [TC-TSTAT-2.2] Setpoint Test Cases with server as DUT"

    def pics_TC_TSTAT_2_2(self):
        """ This function returns a list of PICS for this test case that must be True for the test to be run"""
        return ["TSTAT.S"]

    def steps_TC_TSTAT_2_2(self) -> list[TestStep]:
        steps = [
            TestStep("1", "Commissioning, already done",
                     is_commissioning=True),
            TestStep("2a", "Test Harness Client reads OccupiedCoolingSetpoint from Server DUT and verifies that the value is within range MinCoolSetpointLimit to MaxCoolSetpointLimit, writes a value back that is different but valid, then reads it back again to confirm the successful write.",
                     " Verify that read value is be equal to the written value."),
            # TestStep("2b", "Test Harness Client then attempts to write OccupiedCoolingSetpoint below the MinCoolSetpointLimit and above the MaxCoolSetpointLimit and confirms that the device does not accept the value.",
            #          " Verify that Write command returns the error CONSTRAINT_ERROR (0x87)"),
            # TestStep("2c", "Test Harness Client then attempts to write OccupiedCoolingSetpoint to both of the limits of LowerLimit & MaxCoolSetpointLimit and confirms that the device does accept the value.",
            #          " Verify that Write command succeeds without an error"),
            # TestStep("3a", "Test Harness Client reads OccupiedHeatingSetpoint from Server DUT and verifies that the value is within range MinHeatSetpointLimit to MaxHeatSetpointLimit, writes a value back that is different but valid, then reads it back again to confirm the successful write.",
            #          " Verify that read value is be equal to the written value."),
            # TestStep("3b", "Test Harness Client then attempts to write OccupiedHeatingSetpoint below the MinHeatSetpointLimit and above the MaxHeatSetpointLimit and confirms that the device does not accept the value.",
            #          " Verify that Write command returns the error CONSTRAINT_ERROR (0x87)"),
            # TestStep("3c", "Test Harness Client then attempts to write OccupiedHeatingSetpoint to both of the limits of MinHeatSetpointLimit & UpperLimit and confirms that the device does accept the value.",
            #          " Verify that Write command succeeds without an error"),
            # TestStep("4a", "Test Harness Client reads UnoccupiedCoolingSetpoint from Server DUT and verifies that the value is within range MinCoolSetpointLimit to MaxCoolSetpointLimit, writes a value back that is different but valid6, then reads it back again to confirm the successful write.",
            #          " Verify that read value is be equal to the written value."),
            # TestStep("4b", "Test Harness Client then attempts to write UnoccupiedCoolingSetpoint below the MinCoolSetpointLimit and above the MaxCoolSetpointLimit and confirms that the device does not accept the value.",
            #          " Verify that Write command returns the error CONSTRAINT_ERROR (0x87)"),
            # TestStep("4c", "Test Harness Client then attempts to write UnoccupiedCoolingSetpoint to both of the limits of LowerLimit & MaxCoolSetpointLimit and confirms that the device does accept the value.",
            #          " Verify that Write command succeeds without an error"),
            # TestStep("5a", "Test Harness Client reads UnoccupiedHeatingSetpoint from Server DUT and verifies that the value is within range MinHeatSetpointLimit to MaxHeatSetpointLimit, writes a value back that is different but valid6, then reads it back again to confirm the successful write.",
            #          " Verify that read value is be equal to the written value."),
            # TestStep("5b", "Test Harness Client then attempts to write UnoccupiedHeatingSetpoint below the MinHeatSetpointLimit and above the MaxHeatSetpointLimit and confirms that the device does not accept the value.",
            #          " Verify that Write command returns the error CONSTRAINT_ERROR (0x87)"),
            # TestStep("5c", "Test Harness Client then attempts to write UnoccupiedHeatingSetpoint to both of the limits of MinHeatSetpointLimit & UpperLimit and confirms that the device does accept the value.",
            #          " Verify that Write command succeeds without an error"),
            # TestStep("6a", "Test Harness Client reads MinHeatSetpointLimit from Server DUT and verifies that the value is within range AbsMinHeatSetpointLimit to MaxHeatSetpointLimit, writes a value back that is different but valid3, then reads it back again to confirm the successful write.",
            #          " Verify that read value is equal to the written value."),
            # TestStep("6b", "Test Harness Client then attempts to write MinHeatSetpointLimit below the AbsMinHeatSetpointLimit and above the MaxHeatSetpointLimit and confirms that the device does not accept the value.",
            #          " Verify that Write command returns the error CONSTRAINT_ERROR (0x87)"),
            # TestStep("6c", "Test Harness Client then attempts to write MinHeatSetpointLimit to both of the limits of AbsMinHeatSetpointLimit & UpperLimit and confirms that the device does accept the value.",
            #          " Verify that Write command succeeds without an error"),
            # TestStep("7a", "Test Harness Client reads MaxHeatSetpointLimit from Server DUT and verifies that the value is within range MinHeatSetpointLimit to AbsMaxHeatSetpointLimit, writes a value back that is different but valid4, then reads it back again to confirm the successful write.",
            #          " Verify that read value is equal to the written value."),
            # TestStep("7b", "Test Harness Client then attempts to write MaxHeatSetpointLimit below the MinHeatSetpointLimit and above the AbsMaxHeatSetpointLimit and confirms that the device does not accept the value.",
            #          " Verify that Write command returns the error CONSTRAINT_ERROR (0x87)"),
            # TestStep("7c", "Test Harness Client then attempts to write MaxHeatSetpointLimit to both of the limits of MinHeatSetpointLimit & UpperLimit and confirms that the device does accept the value.",
            #          " Verify that Write command succeeds without an error"),
            # TestStep("8a", "Test Harness Client reads MinCoolSetpointLimit from Server DUT and verifies that the value is within range AbsMinCoolSetpointLimit to MaxCoolSetpointLimit, writes a value back that is different but valid3, then reads it back again to confirm the successful write.",
            #          " Verfy that read value is equal to the written value."),
            # TestStep("8b", "Test Harness Client then attempts to write MinCoolSetpointLimit below the AbsMinCoolSetpointLimit and above the MaxCoolSetpointLimit and confirms that the device does not accept the value.",
            #          " Verify that Write command returns the error CONSTRAINT_ERROR (0x87)"),
            # TestStep("8c", "Test Harness Client then attempts to write MinCoolSetpointLimit to both of the limits of LowerLimit & MaxCoolSetpointLimit and confirms that the device does accept the value.",
            #          " Verify that Write command succeeds without an error"),
            # TestStep("9a", "Test Harness Client reads MaxCoolSetpointLimit from Server DUT and verifies that the value is within range MinCoolSetpointLimit to AbsMaxCoolSetpointLimit, writes a value back that is different but valid4, then reads it back again to confirm the successful write.",
            #          " Verify that read value is equal to the written value."),
            # TestStep("9b", "Test Harness Client then attempts to write MaxCoolSetpointLimit below the MinCoolSetpointLimit and above the AbsMaxCoolSetpointLimit and confirms that the device does not accept the value.",
            #          " Verify that Write command returns the error CONSTRAINT_ERROR (0x87)"),
            # TestStep("9c", "Test Harness Client then attempts to write MaxCoolSetpointLimit to both of the limits of LowerLimit & AbsMaxCoolSetpointLimit and confirms that the device does accept the value.",
            #          " Verify that Write command succeeds without an error"),
            # TestStep("8a", "",
            #          ""),
        ]

        return steps

    @async_test_body
    async def test_TC_TSTAT_2_2(self):
        cluster = Clusters.Thermostat
        endpoint = self.get_endpoint(1)
        attr = cluster.Attributes

        self.step("1")
        # Commission DUT - already done

        minHeatSetpointLimit = 700
        maxHeatSetpointLimit = 3000
        minCoolSetpointLimit = 1600
        maxCoolSetpointLimit = 3200
        absMinHeatSetpointLimit = 700
        absMaxHeatSetpointLimit = 3000
        absMinCoolSetpointLimit = 1600
        absMaxCoolSetpointLimit = 3200
        minSetpointDeadBand = 2500
        occupiedCoolingSetpoint = 2400
        occupiedHeatingSetpoint = 2400
        unoccupiedCoolingSetpoint = 2400
        unoccupiedHeatingSetpoint = 2400

        supportsHeat = self.check_pics("TSTAT.S.F00")
        supportsCool = self.check_pics("TSTAT.S.F01")
        supportsAuto = self.check_pics("TSTAT.S.F05")

        if supportsCool:
            # Saving value for comparision in step 2a read MinCoolSetpointLimit
            if self.check_pics("TSTAT.S.A0017"):
                minCoolSetpointLimit = await self.read_single_attribute_check_success(endpoint=endpoint, cluster=cluster, attribute=attr.MinCoolSetpointLimit)
                # minCoolSetpointLimit = await self.read_single_attribute(dev_ctrl=dev)
            # Saving value for comparision in step 2a read MaxCoolSetpointLimit
            if self.check_pics("TSTAT.S.A0018"):
                maxCoolSetpointLimit = await self.read_single_attribute_check_success(endpoint=endpoint, cluster=cluster, attribute=attr.MaxCoolSetpointLimit)
            # Saving value for comparision in step 8a read attribute AbsMinCoolSetpointLimit
            if self.check_pics("TSTAT.S.A0005"):
                absMinCoolSetpointLimit = await self.read_single_attribute_check_success(endpoint=endpoint, cluster=cluster, attribute=attr.AbsMinCoolSetpointLimit)
            # Saving value for comparision in step9a read attribute AbsMaxCoolSetpointLimit
            if self.check_pics("TSTAT.S.A0006"):
                absMaxCoolSetpointLimit = await self.read_single_attribute_check_success(endpoint=endpoint, cluster=cluster, attribute=attr.AbsMaxCoolSetpointLimit)

            asserts.assert_true(minCoolSetpointLimit <= maxCoolSetpointLimit, "User cool setpoint invalid range")
            asserts.assert_true(absMinCoolSetpointLimit <= absMaxCoolSetpointLimit, "Device cool setpoint invalid range")
            asserts.assert_true(absMinCoolSetpointLimit <= minCoolSetpointLimit, "Invalid User minimum cool setpoint limit")
            asserts.assert_true(maxCoolSetpointLimit <= absMaxCoolSetpointLimit, "Invalid User maximum cool setpoint limit")

        if supportsHeat:
            # Saving value for comparision in step 3a read MinHeatSetpointLimit
            if self.check_pics("TSTAT.S.A0015"):
                minHeatSetpointLimit = await self.read_single_attribute_check_success(endpoint=endpoint, cluster=cluster, attribute=attr.MinHeatSetpointLimit)
            # Saving value for comparision in step 3a read MaxHeatSetpointLimit
            if self.check_pics("TSTAT.S.A0016"):
                maxHeatSetpointLimit = await self.read_single_attribute_check_success(endpoint=endpoint, cluster=cluster, attribute=attr.MaxHeatSetpointLimit)
            # Saving value for comparision in step 6a read attribute AbsMinHeatSetpointLimit
            if self.check_pics("TSTAT.S.A0003"):
                absMinHeatSetpointLimit = await self.read_single_attribute_check_success(endpoint=endpoint, cluster=cluster, attribute=attr.AbsMinHeatSetpointLimit)
            # Saving value for comparision in step 7a read attribute AbsMaxHeatSetpointLimit
            if self.check_pics("TSTAT.S.A0004"):
                absMaxHeatSetpointLimit = await self.read_single_attribute_check_success(endpoint=endpoint, cluster=cluster, attribute=attr.AbsMaxHeatSetpointLimit)

            asserts.assert_true(minHeatSetpointLimit <= maxHeatSetpointLimit, "User heat setpoint invalid range")
            asserts.assert_true(absMinHeatSetpointLimit <= absMaxHeatSetpointLimit, "Device heat setpoint invalid range")
            asserts.assert_true(absMinHeatSetpointLimit <= minHeatSetpointLimit, "Invalid User minimum heat setpoint limit")
            asserts.assert_true(maxHeatSetpointLimit <= absMaxHeatSetpointLimit, "Invalid User maximum heat setpoint limit")

        # Saving value for comparision in step 2c read attribute MinSetpointDeadBand
        if supportsAuto and self.check_pics("TSTAT.S.A0019"):
            minSetpointDeadBand = await self.read_single_attribute_check_success(endpoint=endpoint, cluster=cluster, attribute=attr.MinSetpointDeadBand)

            asserts.assert_true(absMinHeatSetpointLimit <= (absMinCoolSetpointLimit - minSetpointDeadBand),
                                "Invalid device minimum heat setpoint deadband")
            asserts.assert_true(absMaxHeatSetpointLimit <= (absMaxCoolSetpointLimit - minSetpointDeadBand),
                                "Invalid device maximum heat setpoint deadband")
            asserts.assert_true(minHeatSetpointLimit <= (minCoolSetpointLimit - minSetpointDeadBand),
                                "Invalid user minimum heat setpoint deadband")
            asserts.assert_true(maxHeatSetpointLimit <= (maxCoolSetpointLimit - minSetpointDeadBand),
                                "Invalid user maximum heat setpointdeadband")

        # Servers that do not support occupancy are always "occupied"
        occupied = True

        supportsOccupancy = self.check_pics("TSTAT.S.F02")
        if supportsOccupancy:
            occupied = await self.read_single_attribute_check_success(endpoint=endpoint, cluster=cluster, attribute=attr.Occupancy) & 1

        # Target setpoints
        heatSetpoint = minHeatSetpointLimit + ((maxHeatSetpointLimit - minHeatSetpointLimit) / 2)
        coolSetpoint = minCoolSetpointLimit + ((maxCoolSetpointLimit - minCoolSetpointLimit) / 2)

        # Set the heating and cooling setpoints to something other than the target setpoints
        if occupied:
            if supportsHeat:
                await self.write_single_attribute(attribute_value=attr.OccupiedHeatingSetpoint(heatSetpoint), endpoint_id=endpoint)
            if supportsCool:
                await self.write_single_attribute(attribute_value=attr.OccupiedCoolingSetpoint(coolSetpoint), endpoint_id=endpoint)
        else:
            if supportsHeat:
                await self.write_single_attribute(attribute_value=attr.UnoccupiedHeatingSetpoint(heatSetpoint), endpoint_id=endpoint)
            if supportsCool:
                await self.write_single_attribute(attribute_value=attr.UnoccupiedCoolingSetpoint(coolSetpoint), endpoint_id=endpoint)

        # if supportsOccupancy:
        #     # Saving value for comparision in step 3c read attribute OccupiedCoolingSetpoint
        #     if self.check_pics("TSTAT.S.A0011"):
        #         occupiedCoolingSetpoint = await self.read_single_attribute_check_success(endpoint=endpoint, cluster=cluster, attribute=attr.OccupiedCoolingSetpoint)

        #     # Saving value for comparision in step3c read attribute OccupiedHeatingSetpoint
        #     if self.check_pics("TSTAT.S.A0012"):
        #         occupiedHeatingSetpoint = await self.read_single_attribute_check_success(endpoint=endpoint, cluster=cluster, attribute=attr.OccupiedHeatingSetpoint)

        #     # Saving value for comparision in step 3 reads UnoccupiedCoolingSetpoint attribute
        #     if self.check_pics("TSTAT.S.A0013"):
        #         unoccupiedCoolingSetpoint = await self.read_single_attribute_check_success(endpoint=endpoint, cluster=cluster, attribute=attr.UnoccupiedCoolingSetpoint)

        #     # not reading unoccupiedHeatingSetpoint
        #     if self.check_pics("TSTAT.S.A0014"):
        #         pass

        self.step("2a")

        if supportsCool:
            # Step 2a: Test Harness Client reads OccupiedCoolingSetpoint attribute from Server DUT and
            # verifies that the value is within range MinCoolSetpointLimit to MaxCoolSetpointLimit
            if self.check_pics("TSTAT.S.A0011"):
                occupiedCoolingSetpoint = await self.read_single_attribute_check_success(endpoint=endpoint, cluster=cluster, attribute=attr.OccupiedCoolingSetpoint)
            logger.info(f"Verifying occupied cooling setpoint: {occupiedCoolingSetpoint} is between limits")
            asserts.assert_true(minCoolSetpointLimit <= occupiedCoolingSetpoint,
                                "Occupied cooling setpoint is lower than minimum cooling setpoint limit")
            asserts.assert_true(occupiedCoolingSetpoint <= maxCoolSetpointLimit,
                                "Occupied cooling setpoint is greater than maximum cooling setpoint limit")

            # Step 2a: Test Harness Client then attempts to write a value back that is different but valid for OccupiedCoolingSetpoint attribute
            logger.info("Writing back a value that is different but valid for occupied cooling setpoint")
            await self.write_single_attribute(attribute_value=cluster.Attributes.OccupiedCoolingSetpoint(coolSetpoint-1), endpoint_id=endpoint)

            # Step 2a: Test Harness Client reads it back again to confirm the successful write of OccupiedCoolingSetpoint attribute
            newOccupiedCoolingSetpoint = await self.read_single_attribute_check_success(cluster=cluster, endpoint=endpoint, attribute=attr.OccupiedCoolingSetpoint)
            logger.info(f"Verifying new occupied cooling setpoint: {newOccupiedCoolingSetpoint}")
            asserts.assert_true(newOccupiedCoolingSetpoint == (coolSetpoint - 1),
                                "Written and read occupied cooling setpoints are not the same")

        # self.step("2b")


        # self.step("2c")
if __name__ == "__main__":
    default_matter_test_main()
