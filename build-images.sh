#!/bin/bash

# Build the CodeStreamGenerator image
docker build -t csgenerator:latest Containers/CodeStreamGenerator/

# Build the CodeStreamConsumer image
docker build -t csconsumer:latest Containers/CodeStreamConsumer/