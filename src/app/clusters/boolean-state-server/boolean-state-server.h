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
#include <clusters/BooleanState/Events.h>


namespace chip {
namespace app {
namespace Clusters {
namespace BooleanState {

class Delegate;

/**
 * @brief
 *
 */
class BooleanStateServer
{
public:

    /**
     * Creates an boolean state cluster instance.
     * The Init() function needs to be called for this instance to be registered and called by the
     * interaction model at the appropriate times.
     * It is possible to set the CurrentPhase and OperationalState via the Set... methods before calling Init().
     * @param aDelegate A pointer to the delegate to be used by this server.
     * Note: the caller must ensure that the delegate lives throughout the instance's lifetime.
     * @param aEndpointId The endpoint on which this cluster exists. This must match the zap configuration.
     */
    BooleanStateServer(Delegate * aDelegate, chip::EndpointId aEndpointId);

    /**
     * Creates an operational state cluster instance for a given cluster ID.
     * The Init() function needs to be called for this instance to be registered and called by the
     * interaction model at the appropriate times.
     * It is possible to set the CurrentPhase and OperationalState via the Set... methods before calling Init().
     * @param aDelegate A pointer to the delegate to be used by this server.
     * Note: the caller must ensure that the delegate lives throughout the instance's lifetime.
     * @param aEndpointId The endpoint on which this cluster exists. This must match the zap configuration.
     * @param aClusterId The ID of the operational state derived cluster to be instantiated.
     */
    BooleanStateServer(Delegate * aDelegate, chip::EndpointId aEndpointId, chip::ClusterId aClusterId);

    ~BooleanStateServer() = default;

    /**
     * Initialise the boolean state server instance.
     * This function must be called after defining a BooleanStateServer class object.
     * @return Returns an error if the given endpoint and cluster ID have not been enabled in zap or if the
     * CommandHandler or AttributeHandler registration fails, else returns CHIP_NO_ERROR.
     */
    CHIP_ERROR Init();

    static BooleanStateServer & Instance();

    void SetDelegate(Delegate * delegate);

    /**
     * Set current boolean state to state.
     * @param state The boolean state that should now be the current one.
     * @return CHIP_ERROR_READ_FAILED if could not get the actual state. 
     * CHIP_ERROR_WRITE_FAILED if could not set the new state. CHIP_NO_ERROR if set was successful.
     */
    CHIP_ERROR SetStateValue(chip::EndpointId aEndpointId, bool state);

    /**
     * Get the current boolean state value.
     * @return CHIP_ERROR_READ_FAILED if could not get the actual state. CHIP_NO_ERROR if set was successful.
     */
    CHIP_ERROR GetStateValue(chip::EndpointId aEndpointId, bool &value);

private:
    Delegate * mDelegate = nullptr;
    const chip::EndpointId mEndpointId;
    const chip::ClusterId mClusterId;

    BooleanStateServer() = default;
    BooleanStateServer(const BooleanStateServer&) = delete;
    BooleanStateServer& operator=(const BooleanStateServer&) = delete;
    
};

class Delegate
{
public:
    Delegate() = default;

    virtual ~Delegate() = default;

    virtual void OnStateChanged(chip::EndpointId aEndpointId, bool newValue) = 0;

private:
    friend class BooleanStateServer;

    BooleanStateServer * mInstance = nullptr;

    /**
     * This method is used by the SDK to set the instance pointer. This is done during the instantiation of a BooleanStateServer object.
     * @param aInstance A pointer to the BooleanStateServer object related to this delegate object.
     */
    void SetInstance(BooleanStateServer * aInstance) { mInstance = aInstance; }

    BooleanStateServer * Instance() const { return mInstance; }
};

} // namespace BooleanState
} // namespace Clusters
} // namespace app
} // namespace chip