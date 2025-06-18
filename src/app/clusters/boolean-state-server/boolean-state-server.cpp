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

#include "boolean-state-server.h"
#include <app/util/af-types.h>
#include <lib/support/CodeUtils.h>
#include <lib/support/logging/CHIPLogging.h>
#include <protocols/interaction_model/StatusCode.h>
#include <app-common/zap-generated/attributes/Accessors.h>
#include <app/EventLogging.h>



using namespace chip;
using namespace chip::app;
using namespace chip::app::Clusters::BooleanState;

using Status = Protocols::InteractionModel::Status;

BooleanStateServer & BooleanStateServer::Instance()
{
    static BooleanStateServer instance;
    return instance;
}

CHIP_ERROR BooleanStateServer::SetStateValue(chip::EndpointId endpoint, bool state)
{
    bool current;
    Status status = Attributes::StateValue::Get(endpoint, &current);
    if (status != Status::Success)
    {
        ChipLogError(AppServer, "Error reading attribute: %" PRIu8, static_cast<uint8_t>(status));
        return CHIP_ERROR_READ_FAILED;
    }

    if (current == state)
    {
        return CHIP_NO_ERROR;
    }

    status = Attributes::StateValue::Set(endpoint, state);
    if (status != Status::Success)
    {
        ChipLogError(AppServer, "Error writing attribute: %" PRIu8, static_cast<uint8_t>(status));
        return CHIP_ERROR_WRITE_FAILED;
    }

    Events::StateChange::Type event;
    event.stateValue = state;
    EventNumber eventNumber;
    CHIP_ERROR error = LogEvent(event, endpoint, eventNumber);

    if (error != CHIP_NO_ERROR)
    {
        ChipLogError(Zcl, "BooleanStateServer: Failed to record StateChange event: %" CHIP_ERROR_FORMAT, error.Format());
    }

    if (mDelegate)
    {
        mDelegate->OnStateChanged(endpoint, state);
    }

    return CHIP_NO_ERROR;
}

CHIP_ERROR BooleanStateServer::GetStateValue(chip::EndpointId endpoint, bool &value)
{
    Status status = Attributes::StateValue::Get(endpoint, &value);
    if (status != Status::Success)
    {
        ChipLogError(AppServer, "Error reading attribute: %" PRIu8, static_cast<uint8_t>(status));
        return CHIP_ERROR_READ_FAILED;
    }
    
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