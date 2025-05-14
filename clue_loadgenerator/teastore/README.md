# 🏋️ Loadgenerator

The loadgenerator produces http calls tailored to our TeaStore versions.

## General Information

The loadgenerator is written in Python 3.11.0 and requires locust to function.

To install the required packages use
`pip install locust`
or use the provided [requirements.txt](./requirements.txt)

## Components

The loadgenerator consists of the Consumer Behavior Model Graph Component (CBMGC), Endpoint Classes (EC), Loadshape Component (LC) and the configuration component (CC).

The CBMGC and LC are provided to locust as parameters, they provide a User Class and a Test Shape respectively.

The CC loads environment variables and provides them to the other two components.

The ECs are part of the CBMGC Module and provide different ways to send http requests to the TeaStore.
This is required for at least one refactoring we did, where the paths changed.

### Consumer Behavior Model Graph Component

The CBMGC is based on work from [Daniel A. Menascé and others](#citations).

The CBMGC contains a User Class that uses a simple [Finite State Machine](https://en.wikipedia.org/wiki/Finite-state_machine) to determine which pages to access.

### Loadshape Component

The LC is a Child of Locust LoadTestShape Class and provides the number of users that should be active to the Locust runtime.

The Class calculates stages based on a configurable time length, by default an hour and spawns a fraction of a maximum (daily) user number.

Because users are supposed to leave the site after some time and are then stuck in an endless loop, the Loadshape goes to zero in the last seconds of a stage to kill all User Instances.

### Endpoint Classes

There are currently two Endpoint Classes.

1. The Vanilla Class - For the original TeaStore
2. The StaticSiteGeneration Class - That has changed paths for statically generated pages and emulates some http requests that would be handled client side with javascript.

## Manual Execution

To use the loadgenerator, you do not use the scripts or python directly, but instead use locust.

Using `locust -f ./consumerbehavior.py,./loadshapes.py` while inside the /loadgenerator folder will start up locust with the user and the Shape selected.

You can then use the available ways to [configure locust](https://docs.locust.io/en/1.4.3/configuration.html).

Furthermore you can configure the loadshape using the following Environment Variables

| Environment Variable          | Description                                                                                                            |
|:------------------------------|:----------------------------------------------------------------------------------------------------------------------:|
| LOADGENERATOR_MAX_DAILY_USERS | The maximum daily users. In each stage a number of users is spawn, equal to a fraction of this value. Defaults to 1000 |
| LOADGENERATOR_STAGE_DURATION  | The duration of a stage in seconds. Defaults to 3600 (one hour)                                                        |
| LOADGENERATOR_USE_CURRENTTIME | Enables the loadgenerator to use datetime.now() to pickt the current stage. Defaults to True                           |
| LOADGENERATOR_ENDPOINT_NAME   | Choose which routes to use. Defaults to Vanilla                                                                        |

To set an environment variable for the current shell session:

| Shell      | Command                          |
|:-----------|:--------------------------------:|
| Powershell | $env:\<Variable Name\>=\<Value\> |

## Docker usage

### Image

The image uses CMD and provides no ENTRYPOINT.

The image will be hosted at `lierseleow/cnae-loadgenerator` till at least the 01.10.2023.

### Default Environment Variables

The following variables are set in the container:

- `LOCUST_HOST` is set to `http://localhost/tools.descartes.teastore.webui/:8080`
- `LOCUST_HEADLESS` is set to `yes`

## Helm Chart Usage

The values.yaml has the following additional variables to be set, that correspond to Environment Variables.

| Value                           | Environment Variable          | Default                 |
|:--------------------------------|:-----------------------------:|:-----------------------:|
| loadgenerator.dailyUsers        | LOADGENERATOR_MAX_DAILY_USERS | 1000                    |
| loadgenerator.stageDuration     | LOADGENERATOR_STAGE_DURATION  | 3600                    |
| loadgenerator.useActualTime     | LOADGENERATOR_USE_CURRENTTIME | True                    |
| loadgenerator.endpointClassName | LOADGENERATOR_ENDPOINT_NAME   | Vanilla                 |
| loadgenerator.targetHost        | LOCUST_HOST                   | `http://teastore-webui.st-cnae-g5.svc.cluster.local:8080/tools.descartes.teastore.webui/` |
| loadgenerator.webPort           | LOCUST_WEB_PORT               | 8080                    |
| loadgenerator.headless          | LOCUST_HEADLESS               | yes                     |

## Citations

1. Daniel A. Menascé, Virgilio A. F. Almeida, Rodrigo Fonseca, and Marco A. Mendes.; "A methodology for workload characterization of E-commerce sites"; In Proceedings of the 1st ACM conference on Electronic commerce (EC '99); Association for Computing Machinery, New York, NY, USA 119–128; 1999; https://doi.org/10.1145/336992.337024
2. D. A. Menasce; "TPC-W: a benchmark for e-commerce"; in IEEE Internet Computing, vol. 6, no. 3, pp. 83-87; May-June 2002; https://doi.org/10.1109/MIC.2002.1003136
