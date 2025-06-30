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

#include <app/AttributeAccessInterface.h>
#include <app/util/af-types.h>
#include <app/util/attribute-storage.h>
#include <clusters/BooleanState/Events.h>
#include <app-common/zap-generated/attributes/Accessors.h>
#include <app-common/zap-generated/enums.h>
#include <protocols/interaction_model/StatusCode.h>
#include <lib/core/CHIPError.h>

namespace chip {
namespace app {
namespace Clusters {
namespace BooleanState {

class Delegate;

class BooleanStateServer : public AttributeAccessInterface
{
public:
    static BooleanStateServer & Instance();

    CHIP_ERROR Init();
    void SetDelegate(Delegate * delegate);

    CHIP_ERROR SetStateValue(EndpointId aEndpointId, bool newState);
    CHIP_ERROR GetStateValue(EndpointId aEndpointId, bool & value) const;

private:
    Delegate * mDelegate = nullptr;
    
    BooleanStateServer();
    BooleanStateServer(const BooleanStateServer&) = delete;
    BooleanStateServer& operator=(const BooleanStateServer&) = delete;

    // AttributeAccessInterface overrides
    CHIP_ERROR Read(const ConcreteReadAttributePath & aPath, AttributeValueEncoder & aEncoder) override;
    CHIP_ERROR Write(const ConcreteWriteAttributePath & aPath, AttributeValueDecoder & aDecoder) override;
};

class Delegate
{
public:
    virtual ~Delegate() = default;
    virtual void OnStateChanged(EndpointId aEndpointId, bool newValue) = 0;

private:
    friend class BooleanStateServer;
    BooleanStateServer * mInstance = nullptr;

    void SetInstance(BooleanStateServer * aInstance) { mInstance = aInstance; }
    BooleanStateServer * Instance() const { return mInstance; }
};

} // namespace BooleanState
} // namespace Clusters
} // namespace app
} // namespace chip