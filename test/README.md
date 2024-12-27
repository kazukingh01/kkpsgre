# Preparation of Environment for Test !!


### Common

```bash
mkdir -p /home/share/
sudo docker network create --subnet=99.99.0.0/16 testnw99
```

### PostgreSQL
    -v /var/local/postgresql/data:/var/lib/postgresql/data \

```bash
POSTGRESQL_VER="16.4"
echo "FROM postgres:${POSTGRESQL_VER}" > ./Dockerfile
echo "RUN apt-get update" >> ./Dockerfile
echo "RUN apt-get install -y locales" >> ./Dockerfile
echo "RUN rm -rf /var/lib/apt/lists/*" >> ./Dockerfile
echo "RUN localedef -i ja_JP -c -f UTF-8 -A /usr/share/locale/locale.alias ja_JP.UTF-8" >> ./Dockerfile
echo "ENV LANG=ja_JP.utf8" >> ./Dockerfile
sudo docker image build -t postgres:${POSTGRESQL_VER}.jp .
sudo docker run --name test_postgres \
    -e POSTGRES_PASSWORD=postgres \
    -e POSTGRES_INITDB_ARGS="--encoding=UTF8 --locale=ja_JP.utf8" \
    -e TZ=Asia/Tokyo \
    -v /home/share:/home/share \
    --net=testnw99 --ip=99.99.0.2 \
    --shm-size=4g \
    -d postgres:${POSTGRESQL_VER}.jp
sudo apt update && sudo apt install -y postgresql-client
psql "postgresql://postgres:postgres@99.99.0.2:5432/" # \q to exit. 
sudo docker exec --user=postgres test_postgres createdb --encoding=UTF8 --locale=ja_JP.utf8 --template=template0 --port 5432 testdb
```

### MySQL

    -v /var/local/mysql:/var/lib/mysql \

```bash
MYSQL_VER="8.0.39-debian"
echo "FROM mysql:${MYSQL_VER}" > ./Dockerfile
echo "RUN apt-get update" >> ./Dockerfile
echo "RUN apt-get install -y locales" >> ./Dockerfile
echo "RUN rm -rf /var/lib/apt/lists/*" >> ./Dockerfile
echo "RUN echo "ja_JP.UTF-8 UTF-8" > /etc/locale.gen" >> ./Dockerfile
echo "RUN locale-gen ja_JP.UTF-8" >> ./Dockerfile
echo "ENV LC_ALL=ja_JP.UTF-8" >> ./Dockerfile
echo "RUN echo '[mysqld]'                            >  /etc/mysql/conf.d/charset.cnf" >> ./Dockerfile
echo "RUN echo 'character-set-server=utf8mb4'        >> /etc/mysql/conf.d/charset.cnf" >> ./Dockerfile
echo "RUN echo 'collation-server=utf8mb4_general_ci' >> /etc/mysql/conf.d/charset.cnf" >> ./Dockerfile
echo "RUN echo '[mysql]'                             >> /etc/mysql/conf.d/charset.cnf" >> ./Dockerfile
echo "RUN echo 'default-character-set=utf8mb4'       >> /etc/mysql/conf.d/charset.cnf" >> ./Dockerfile
echo "RUN echo '[client]'                            >> /etc/mysql/conf.d/charset.cnf" >> ./Dockerfile
echo "RUN echo 'default-character-set=utf8mb4'       >> /etc/mysql/conf.d/charset.cnf" >> ./Dockerfile
sudo docker image build -t mysql:${MYSQL_VER}.jp .
sudo docker run --name test_mysql \
    -e MYSQL_ROOT_PASSWORD=mysql \
    -e MYSQL_USER=mysql \
    -e MYSQL_PASSWORD=mysql \
    -e MYSQL_DATABASE=testdb \
    -e MYSQL_PORT=3306 \
    -e TZ=Asia/Tokyo \
    -v /home/share:/home/share \
    --net=testnw99 --ip=99.99.0.3 \
    --shm-size=4g \
    -d mysql:${MYSQL_VER}.jp
sudo apt update && sudo apt install -y mysql-client
mysql -h 99.99.0.3 -P 3306 -u mysql --password=mysql # USE testdb; SHOW TABLES;
```

### MongoDB

```bash
MONGODB_VER="7.0.16"
echo "FROM mongo:${MONGODB_VER}" > ./Dockerfile
echo "RUN apt-get update" >> ./Dockerfile
echo "RUN apt-get install -y locales" >> ./Dockerfile
echo "RUN rm -rf /var/lib/apt/lists/*" >> ./Dockerfile
echo "RUN localedef -i ja_JP -c -f UTF-8 -A /usr/share/locale/locale.alias ja_JP.UTF-8" >> ./Dockerfile
echo "ENV LANG=ja_JP.utf8" >> ./Dockerfile
sudo docker image build -t mongo:${MONGODB_VER}.jp .
sudo mkdir -p /var/local/mongodb/data
sudo docker run --name test_mongo \
    -e MONGO_INITDB_ROOT_USERNAME=root \
    -e MONGO_INITDB_ROOT_PASSWORD=secret \
    -e TZ=Asia/Tokyo \
    -v /home/share:/home/share \
    --net=testnw99 --ip=99.99.0.4 \
    --shm-size=4g \
    -d mongo:${MONGODB_VER}.jp
sudo apt update && sudo apt install -y mongodb-clients
mongo --host 99.99.0.4 --port 27017 -u root -p secret --authenticationDatabase "admin" # quit() to exit
```

### Create tables

```bash
cp ./schema.psgre.sql /home/share/
sudo docker exec --user=postgres test_postgres psql -U postgres -p 5432 -d testdb -f /home/share/schema.psgre.sql
cp ./schema.mysql.sql /home/share/
sudo docker exec test_mysql /bin/sh -c "mysql --password=mysql --database=testdb < /home/share/schema.mysql.sql"
cp ./schema.mongo.js /home/share/
sudo docker exec test_mongo mongosh admin -u root -p secret --port 27017 --eval 'load("/home/share/schema.mongo.js");'
```