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

class Delegate
{
public:
    Delegate() = default;

    virtual ~Delegate() = default;

    virtual void OnStateChanged(chip::EndpointId endpoint, bool newValue) = 0;

private:
    friend class BooleanStateServer;

    BooleanStateServer * mInstance = nullptr;

    /**
     * This method is used by the SDK to set the instance pointer. This is done during the instantiation of a Instance object.
     * @param aInstance A pointer to the Instance object related to this delegate object.
     */
    void SetInstance(BooleanStateServer * aInstance) { mInstance = aInstance; }

    BooleanStateServer * Instance() const { return mInstance; }
};

/**
 * @brief
 *
 */
class BooleanStateServer
{
public:

    static BooleanStateServer & Instance();

    void SetDelegate(Delegate * delegate);

    CHIP_ERROR SetStateValue(chip::EndpointId endpoint, bool state);

    /**
     * Get the current boolean state.
     * @return The current boolean state value.
     */
    CHIP_ERROR GetStateValue(chip::EndpointId, bool &value);

private:
    Delegate * mDelegate = nullptr;

    BooleanStateServer() = default;
    BooleanStateServer(const BooleanStateServer&) = delete;
    BooleanStateServer& operator=(const BooleanStateServer&) = delete;
    
};

} // namespace BooleanState
} // namespace Clusters
} // namespace app
} // namespace chip