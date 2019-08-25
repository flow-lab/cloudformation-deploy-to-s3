DEPLOYMENT_BUCKET_NAME ?= webbapp-deployment-packaging
DEPLOYMENT_KEY := $(shell echo webbapp-deployment-packaging-$$RANDOM.zip)
STACK_NAME ?= webbapp-deployment-packaging
PROFILE ?= cloudformation@flowlab-development

clean:
	rm -rf build

build/python:
	mkdir -p build/python

build/python/deployer.py: src/deployer.py build/python
	cp $< $@

build/python/dependencies: build/python
	pip install requests --target build/python
	pip install pathspec --target build/python
	pip install semver --target build/python

build: build/python/deployer.py build/python/dependencies

build/layer.zip:
	cd build/ && zip -r layer.zip python

deploy: cloudformation/template.yml build/layer.zip
	aws --profile $(PROFILE) s3 cp build/layer.zip s3://$(DEPLOYMENT_BUCKET_NAME)/$(DEPLOYMENT_KEY)
	aws --profile $(PROFILE) cloudformation deploy --template-file cloudformation/template.yml --stack-name $(STACK_NAME) --capabilities CAPABILITY_IAM --parameter-overrides DeploymentBucketName=$(DEPLOYMENT_BUCKET_NAME) DeploymentKey=$(DEPLOYMENT_KEY) LayerName=$(STACK_NAME)
	aws --profile $(PROFILE) cloudformation describe-stacks --stack-name $(STACK_NAME) --query Stacks[].Outputs[].OutputValue --output text
