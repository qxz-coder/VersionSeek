#!/bin/bash

# process paras
## select workspace
workspace=
if [ ! -n "$1" ]; then
    echo "[-]:need worksapce para"
    exit
else
    workspace=$1
    echo "[+]:workspace is $workspace"
fi


## select version number
## TODO: add versionNumber list
versionNumber=
if [ ! -n "$2" ]; then
    echo "[-]:need versionNumber para"
    exit
else
    versionNumber=$2
    echo "[+]:versionNumber is $versionNumber"
fi


## select port
port=$3
if [ ! -n "$3" ]; then
    echo "[-]:need port para"
    exit
else
    echo "[+]:port is $versionNumber"
fi


## select zookeeper ip
zookeeperIp=$4
if [ ! -n "$4" ]; then
    echo "[-]:need zookeeperIp para"
    exit
else
    echo "[+]:zookeeperIp is $zookeeperIp"
fi


# process version
versionInt=`echo $versionNumber | awk -F. '{print $1$2$3}'`
dockerDir=`echo $versionNumber | awk -F. -vb=dubbo_ -va=_ '{print b$1a$2a$3}'`
container_name=`echo $versionNumber | awk -F. -vb=DUBBO_ -va=_ '{print b$1a$2a$3}'`
serviceName=`echo $versionNumber | awk -F. -vb=dubbo -va=_ '{print b$1a$2a$3}'`

echo "[+]:dockerDir is $dockerDir"
# generate dubbo dir
cd $workspace
if [ ! -d "./${dockerDir}" ]; then
    mkdir ${dockerDir}
fi


# modify Dockerfile
if [ ! -f "Dubbo_docker_25" ]; then
    echo "[-]: Dubbo dockerfile template is missing!"
    exit
fi

cat "Dubbo_docker_25" > "${dockerDir}/Dockerfile"
sed -i "s/xx.xx.xx.xx/${zookeeperIp}/g" "${dockerDir}/Dockerfile"



# generate docker-compose.yml
cd $dockerDir
echo "version: ''" > docker-compose.yml
echo "services:" >> docker-compose.yml
echo "  ${serviceName}:" >> docker-compose.yml
echo "    container_name: $container_name" >> docker-compose.yml
echo "    build: ." >> docker-compose.yml
echo "    ports:" >> docker-compose.yml
echo "     - $port:20880" >> docker-compose.yml
echo "    networks:" >> docker-compose.yml
echo "     - dubbo" >> docker-compose.yml

echo "networks:" >> docker-compose.yml
echo "  dubbo:" >> docker-compose.yml
echo "    external: true" >> docker-compose.yml


git clone -b dubbo-${versionNumber} https://githubfast.com/dubbo/dubbo.git ./dubbo
# # start docker container
docker compose build && docker compose up -d
