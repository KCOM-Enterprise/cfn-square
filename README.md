# cfn-square

[![Build Status](https://travis-ci.org/KCOM-Enterprise/cfn-square.svg?branch=master)](https://travis-ci.org/KCOM-Enterprise/cfn-square)

A CLI tool intended to simplify AWS CloudFormation handling. Originally forked from cfn-sphere.

## Features

### cfn-sphere

- cfn templates in yaml or json
- build for human interaction and automation (run 'cf sync stacks.yml' triggered by a git push if you dare ;-)
- a source of truth defining CloudFormation stacks with their template and parameters
- cross referencing parameters between stacks (use a stack output as parameter for another stack)
- automatic stack dependency resolution including circular dependency detection
- helper features easing the use of cfn functions like Fn::Join, Ref or Fn::GetAtt
- easy user-data definition for https://github.com/zalando-stups/taupage
- allow stack parameter values updates in command line interface 
- encrypt/decrypt values with AWS KMS (https://aws.amazon.com/de/kms/)

### cfn-square additional features

- Support for creating and executing CloudFormation change sets

## Install

### As Python artifact:

    pip install cfn-square

## Usage

    $ cf --help
    Usage: cf [OPTIONS] COMMAND [ARGS]...
    
      This tool manages AWS CloudFormation templates and stacks by providing an
      application scope and useful tooling.

    Options:
      --version  Show the version and exit.
      --help     Show this message and exit.

    Commands:
      convert             Convert JSON to YAML or vice versa
      create-change-set   create change set
      decrypt             Decrypt a given ciphertext with AWS Key Management Service
      delete              Delete all stacks in a stack configuration
      encrypt             Encrypt a given string with AWS Key Management Service
      execute-change-set  execute change set
      render-template     Render template as it would be used to create/update a stack
      sync                Sync AWS resources with definition file
      validate-template   Validate template with CloudFormation API

## Getting Started with the sync command

### 1. Create Stacks Config

Create a YAML file containing a region and some stacks in a stacks.yml file f.e.:

    region: eu-west-1
    stacks:
        test-vpc:
            template-url: vpc.yml
        test-stack:
            template-url: app.yml
            parameters:
                vpcID: "|ref|test-vpc.id"

### 2. Write your CloudFormation templates

Write your templates and configure them in your stacks.yml. Optionally you can define 
placeholders in your stack config using the [to-be-replaced] notation and supply a
'transforms context' file.

##### Example

stacks.yml:

    region: eu-west-1
    stacks:
        test-vpc:
            template-url: vpc.yml
            name: vpc[environment]
        test-stack:
            template-url: app.yml
            parameters:
                vpcID: "|ref|test-vpc.id"

##### Context (development environment):

dev.yml

    environment: dev

staging.yml:

    environment: staging

production.yml:

    environment: production

This way your stacks.yml remains the same for all the environments.

### 3. Configure the account profile

cfn-square supports assuming AWS roles. The AWS CLI looks for role configurations in the user config file, located at `~/.aws/config`. Each profile requires at least these properties to be configured:

    [default]
    region = eu-west-1
    output = json
     
    [profile accountrole]
    source_profile = default
    mfa_serial = arn:aws:iam::987654321987:mfa/jsmith.kcom.adm
    role_arn = arn:aws:iam::123456789123:role/CA_KCOM_ADM

You need the `mfa_serial` for your admin user, and the `role_arn` of the admin role for the account. The AWS Practice Confluence page on cross account access explains this in more detail.

- `mfa_serial` can be found attached to your IAM user entry in your admin account.
- To find the `role_arn` for the role that you need to assume, identify the environment that you intend to modify on the Admin Roles list on the AWS Sharepoint. Log in to the role with the link associated with the account, and you can find the ARN attached to the `CA_KCOM_ADM` role in that account's IAM.

### 4. Sync it

A single command synchronizes your definition with reality!

    cf sync stack.yml -t dev.yml --profile accountrole

## Other features

##### Creating CloudFormation change sets

cfn-square can be used to create a change set based on the delta between an AWS account and your local config:

    cf create-change-set stack.yml -t transforms.yml --profile accountrole

This creates a change set for each stack if it differs from your specified local config.

##### Executing CloudFormation change sets

cfn-square can also be used to execute change sets:

    cf execute-change-set changeSetName --profile accountrole

`changeSetName` should be replaced with the name or ARN of the change set.

##### Parameterise Stack with CLI parameters

To pass stack parameters without having to modify the templates, simply use the `--parameter` or `-p` flag.

    cf sync --parameter "test-stack.vpcID=vpc-123" --parameter "test-stack.subnetID=subnet-234" myapp-test.yml

## Documentation

### cfn-sphere documentation

For original cfn-sphere features read:

**https://github.com/cfn-sphere/cfn-sphere/wiki**

### cfn-square documentation

For cfn-square specific features read:

**https://github.com/KCOM-Enterprise/cfn-square/wiki**

### Config reference

See the wiki to see what you can do in a stack configuration: [StackConfig Reference](https://github.com/cfn-sphere/cfn-sphere/wiki/StackConfig-Reference)

### Template reference

Cfn-Sphere supports native CloudFormation templates written in JSON or YAML, located in local filesystem or s3. There are some improvements like simplified intrinsic functions one can use. See the reference for details: [Template Reference](https://github.com/cfn-sphere/cfn-sphere/wiki/Template-Reference)

## Build

Requirements:

* python >= 3
* virtualenv
* pybuilder

Execute:

    git clone git@github.com:KCOM-Enterprise/cfn-square.git
    cd cfn-square
    virtualenv .venv --python=python3
    source .venv/bin/activate
    pip install pybuilder
    pyb install_dependencies
    pyb

## Contribution

* Create an issue to discuss the problem and track changes for future releases
* Create a pull request with your changes (as small as possible to ease code reviews)

## License

Copyright 2015,2016 Marco Hoyer
Copyright 2017 KCOM

Licensed under the Apache License, Version 2.0 (the "License"); you may not use
this file except in compliance with the License. You may obtain a copy of the
License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
