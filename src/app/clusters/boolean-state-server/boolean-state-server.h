/*
 *
 *    Copyright (c) 2025 Project CHIP Authors
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

#pragma once

#include <app/util/af-types.h>
// #include <app/util/basic-types.h>
// #include <platform/CHIPDeviceConfig.h>


namespace chip {
namespace app {
namespace Clusters {
namespace BooleanState {


/**
 * @brief
 *
 */
class BooleanStateServer
{
public:

    /**
     * Creates an operational state cluster instance.
     * The Init() function needs to be called for this instance to be registered and called by the
     * interaction model at the appropriate times.
     * It is possible to set the CurrentPhase and OperationalState via the Set... methods before calling Init().
     * @param aDelegate A pointer to the delegate to be used by this server.
     * Note: the caller must ensure that the delegate lives throughout the instance's lifetime.
     * @param aEndpointId The endpoint on which this cluster exists. This must match the zap configuration.
     */
    static BooleanStateServer & Instance();

    /**
     * Set current state value to state and the operational error to kNoError.
     * NOTE: This method cannot be used to set the error state. The error state must be set via the
     * OnOperationalErrorDetected method.
     * @param endpoint The operational state that should now be the current one.
     * @return CHIP_ERROR_INVALID_ARGUMENT if endpoint and state are invalid values. CHIP_NO_ERROR if set was successful.
     */
    CHIP_ERROR SetStateValue(chip::EndpointId endpoint, bool state);

    /**
     * Get the current boolean state.
     * @return The current boolean state value.
     */
    bool GetStateValue(chip::EndpointId);

private:

    BooleanStateServer() = default;
    static BooleanStateServer instance;
};

} // namespace BooleanState
} // namespace Clusters
} // namespace app
} // namespace chip