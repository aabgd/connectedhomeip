/**
 *
 *    Copyright (c) 2020 Project CHIP Authors
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

/****************************************************************************'
 * @file
 * @brief Implementation for the Boolean State Server Cluster
 ***************************************************************************/

#include "boolean-state-server.h"
#include <app/util/af-types.h>
#include <lib/support/CodeUtils.h>
#include <lib/support/logging/CHIPLogging.h>
#include <protocols/interaction_model/StatusCode.h>
#include <app-common/zap-generated/attributes/Accessors.h>
#include <app-common/zap-generated/callback.h>
#include <app/EventLogging.h>
#include <app/util/attribute-storage.h>
#include <app/AttributeAccessInterface.h>


using namespace chip;
using namespace chip::app;
using namespace chip::app::Clusters;
using namespace chip::app::Clusters::BooleanState;
using namespace chip::app::Clusters::BooleanState::Attributes;

using Status = Protocols::InteractionModel::Status;


BooleanStateServer & BooleanStateServer::Instance()
{
    static BooleanStateServer instance;
    return instance;
}

BooleanStateServer::BooleanStateServer() :
    AttributeAccessInterface(Optional<EndpointId>(), BooleanState::Id) 
{}

CHIP_ERROR BooleanStateServer::Init()
{
    VerifyOrReturnError(AttributeAccessInterfaceRegistry::Instance().Register(this), CHIP_ERROR_INCORRECT_STATE);
    return CHIP_NO_ERROR;
}

void BooleanStateServer::SetDelegate(Delegate * delegate)
{
    mDelegate = delegate;
    if (mDelegate != nullptr)
    {
        mDelegate->SetInstance(this);
    }
}

CHIP_ERROR BooleanStateServer::SetStateValue(EndpointId aEndpointId, bool newState)
{
    bool currState;
    Status status = Attributes::StateValue::Get(aEndpointId, &currState);
    if (status != Status::Success)
    {
        ChipLogError(AppServer, "Error reading attribute: %" PRIu8, static_cast<uint8_t>(status));
        return CHIP_ERROR_READ_FAILED;
    }

    if (currState == newState)
    {
        return CHIP_NO_ERROR;
    }

    status = Attributes::StateValue::Set(aEndpointId, newState);
    if (status != Status::Success)
    {
        ChipLogError(AppServer, "Error writing attribute: %" PRIu8, static_cast<uint8_t>(status));
        return CHIP_ERROR_WRITE_FAILED;
    }

    Events::StateChange::Type event;
    event.stateValue = newState;
    EventNumber eventNumber;
    CHIP_ERROR error = LogEvent(event, aEndpointId, eventNumber);

    if (error != CHIP_NO_ERROR)
    {
        ChipLogError(Zcl, "BooleanStateServer: Failed to record StateChange event: %" CHIP_ERROR_FORMAT, error.Format());
    }

    if (mDelegate)
    {
        mDelegate->OnStateChanged(aEndpointId, newState);
    }

    return CHIP_NO_ERROR;
}

CHIP_ERROR BooleanStateServer::GetStateValue(EndpointId aEndpointId, bool &value) const
{
    Status status = Attributes::StateValue::Get(aEndpointId, &value);
    if (status != Status::Success)
    {
        ChipLogError(AppServer, "Error reading attribute: %" PRIu8, static_cast<uint8_t>(status));
        return CHIP_ERROR_READ_FAILED;
    }
    
    return CHIP_NO_ERROR;
}

CHIP_ERROR BooleanStateServer::Read(const ConcreteReadAttributePath & aPath, AttributeValueEncoder & aEncoder)
{
    if (aPath.mAttributeId == Attributes::StateValue::Id)
    {
        bool value;
        ReturnErrorOnFailure(GetStateValue(aPath.mEndpointId, value));
        return aEncoder.Encode(value);
    }

    return CHIP_NO_ERROR;
}

CHIP_ERROR BooleanStateServer::Write(const ConcreteWriteAttributePath & aPath, AttributeValueDecoder & aDecoder)
{
    if (aPath.mAttributeId == Attributes::StateValue::Id)
    {
        bool value;
        ReturnErrorOnFailure(aDecoder.Decode(value));
        return SetStateValue(aPath.mEndpointId, value);
    }

    return CHIP_ERROR_UNSUPPORTED_CHIP_FEATURE;
}