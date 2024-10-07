# kkpsgre

Dataframe interface for PostgreSQL

# PostgreSQL

There are 3 options.

- Create database by using docker (use docker hub)
- Create database by using docker (manually install in ubuntu) 
- Create database on host server

### Install ( Docker Hub Base )

```bash
PASSPSQL=`openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 16`
echo ${PASSPSQL} > ~/passpsql.txt
POSTGRESQL_VER="16.4"
echo "FROM postgres:${POSTGRESQL_VER}" > ~/Dockerfile
echo "RUN apt-get update" >> ~/Dockerfile
echo "RUN apt-get install -y locales" >> ~/Dockerfile
echo "RUN rm -rf /var/lib/apt/lists/*" >> ~/Dockerfile
echo "RUN localedef -i ja_JP -c -f UTF-8 -A /usr/share/locale/locale.alias ja_JP.UTF-8" >> ~/Dockerfile
echo "ENV LANG=ja_JP.utf8" >> ~/Dockerfile
sudo docker image build -t postgres:${POSTGRESQL_VER}.jp .
sudo mkdir -p /var/local/postgresql/data # This case
sudo docker network create --subnet=172.18.0.0/16 dbnw
sudo docker run --name postgres \
    -e POSTGRES_PASSWORD=${PASSPSQL} \
    -e POSTGRES_INITDB_ARGS="--encoding=UTF8 --locale=ja_JP.utf8" \
    -e TZ=Asia/Tokyo \
    -v /var/local/postgresql/data:/var/lib/postgresql/data \
    -v /home/share:/home/share \
    --net=dbnw --ip=172.18.0.2 \
    --shm-size=4g \
    -d postgres:${POSTGRESQL_VER}.jp
sudo apt update && sudo apt install -y postgresql-client
psql "postgresql://postgres:`cat ~/passpsql.txt`@172.18.0.2:5432/"
```

Write below to be enable restarting after reboot.

```bash
sudo touch /etc/rc.local
sudo chmod 700 /etc/rc.local
sudo bash -c "echo \#\!/bin/bash >> /etc/rc.local"
sudo bash -c "echo docker restart postgres >> /etc/rc.local"
sudo systemctl restart rc-local.service
```

Add port forward rules.

```bash
sudo vi /etc/ufw/before.rules
```

```diff
#
# rules.before
#
# Rules that should be run before the ufw command line added rules. Custom
# rules should be added to one of these chains:
#   ufw-before-input
#   ufw-before-output
#   ufw-before-forward
#

+*nat
+-F
+:PREROUTING ACCEPT [0:0]
+:POSTROUTING ACCEPT [0:0]

+-A PREROUTING  -p tcp -i eth0            -s 0.0.0.0/0 --dport 65432 -j DNAT --to-destination 172.18.0.2:5432
+-A POSTROUTING -p tcp -o br-cc53ebc221ce -s 172.18.0.0/16 -j MASQUERADE

+COMMIT

# Don't delete these required lines, otherwise there will be errors
*filter*nat
...
```

```bash
sudo sed -i 's/^#net\/ipv4\/ip_forward=1/net\/ipv4\/ip_forward=1/' /etc/ufw/sysctl.conf
sudo sed -i 's/DEFAULT_FORWARD_POLICY="DROP"/DEFAULT_FORWARD_POLICY="ACCEPT"/' /etc/default/ufw
sudo ufw disable
sudo ufw enable
# You don't need to set 'sudo ufw allow 65432'
```

### Install ( Docker Ubuntu Base )

##### ubuntu container & exec /bin/bash

```bash
sudo docker pull ubuntu:22.04
sudo docker run -itd -v /home/share:/home/share -p 65432:5432 --name postgres ubuntu:22.04 /bin/sh # It's better to be changed port no.
sudo docker exec -it postgres /bin/bash
```

##### install postgresql

```bash
apt-get update
UBUNTU_CODENAME=`cat /etc/os-release | grep UBUNTU_CODENAME | cut -d '=' -f 2`
echo "deb http://apt.postgresql.org/pub/repos/apt/ ${UBUNTU_CODENAME}-pgdg main" | tee -a /etc/apt/sources.list.d/pgdg.list
# "focal" is Ubuntu CODE Name. check with `cat /etc/os-release` "UBUNTU_CODENAME"
apt-get install -y apt-transport-https ca-certificates curl software-properties-common openssh-client vim
curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
apt-get update
apt-get install -y postgresql-16 # check "apt search postgresql"
```

##### Locale setting

```bash
apt-get install -y language-pack-ja
locale -a
# C
# C.utf8
# POSIX
# ja_JP.utf8
```

##### DB initialize

```bash
su postgres
cd ~
mkdir /var/lib/postgresql/data
/usr/lib/postgresql/16/bin/initdb -D /var/lib/postgresql/data -E UTF8
```

##### Start & Check & Change Password

```bash
exit
/etc/init.d/postgresql restart # for root user
su postgres
psql
\l
# postgres=# \l
#                                                    List of databases
#    Name    |  Owner   | Encoding | Locale Provider | Collate |  Ctype  | ICU Locale | ICU Rules |   Access privileges
# -----------+----------+----------+-----------------+---------+---------+------------+-----------+-----------------------
#  postgres  | postgres | UTF8     | libc            | C.UTF-8 | C.UTF-8 |            |           |
#  template0 | postgres | UTF8     | libc            | C.UTF-8 | C.UTF-8 |            |           | =c/postgres          +
#            |          |          |                 |         |         |            |           | postgres=CTc/postgres
#  template1 | postgres | UTF8     | libc            | C.UTF-8 | C.UTF-8 |            |           | =c/postgres          +
#            |          |          |                 |         |         |            |           | postgres=CTc/postgres
# (3 rows)
alter role postgres with password 'postgres';
\q
```

##### Docker Save ( If you need )

```bash
exit
sudo docker stop postgres
sudo docker commit postgres postgres:XX.X # save image
sudo docker save postgres:XX.X > postgres_XX.X.tar # export tar
sudo docker rm postgres
```

### Install ( Host Base )

##### Install PostgreSQL

```bash
sudo apt-get update
UBUNTU_CODENAME=`cat /etc/os-release | grep UBUNTU_CODENAME | cut -d '=' -f 2`
echo "deb http://apt.postgresql.org/pub/repos/apt/ ${UBUNTU_CODENAME}-pgdg main" | sudo tee -a /etc/apt/sources.list.d/pgdg.list
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt-get update
sudo apt-get install -y postgresql-16 # check "apt search postgresql"
```

##### Locale setting

```bash
sudo apt-get install -y language-pack-ja
locale -a
# C
# C.utf8
# POSIX
# ja_JP.utf8
```

##### DB initialize

```bash
sudo su postgres
cd ~
mkdir /var/lib/postgresql/data
/usr/lib/postgresql/16/bin/initdb -D /var/lib/postgresql/data -E UTF8
```

##### Start & Check & Change Password

```bash
exit
sudo /etc/init.d/postgresql restart # for ubuntu user
sudo su postgres
psql
\l
# postgres=# \l
#                                                    List of databases
#    Name    |  Owner   | Encoding | Locale Provider | Collate |  Ctype  | ICU Locale | ICU Rules |   Access privileges
# -----------+----------+----------+-----------------+---------+---------+------------+-----------+-----------------------
#  postgres  | postgres | UTF8     | libc            | C.UTF-8 | C.UTF-8 |            |           |
#  template0 | postgres | UTF8     | libc            | C.UTF-8 | C.UTF-8 |            |           | =c/postgres          +
#            |          |          |                 |         |         |            |           | postgres=CTc/postgres
#  template1 | postgres | UTF8     | libc            | C.UTF-8 | C.UTF-8 |            |           | =c/postgres          +
#            |          |          |                 |         |         |            |           | postgres=CTc/postgres
# (3 rows)
alter role postgres with password 'postgres';
\q
```

### PostgreSQL Config

( Host )

```bash
vi /etc/postgresql/16/main/postgresql.conf
```

( Docker Hub )

```bash
sudo docker exec -it postgres /bin/bash
vi /etc/postgresql/16/main/postgresql.conf
```

( Docker Ubuntu )

```bash
sudo docker exec -it postgres /bin/bash
vi /var/lib/postgresql/data/postgresql.conf
```

```postgresql.conf
shared_buffers = 2GB                    # Set 40% of RAM
work_mem = 256MB                        # min 64kB
effective_cache_size = 16GB
listen_addresses = '*'                  # what IP address(es) to listen on;
port = 5432                             # (change requires restart)
autovacuum = on                         # Enable autovacuum subprocess?  'on'
autovacuum_max_workers = 4              # max number of autovacuum subprocesses
maintenance_work_mem = 1GB              # min 1MB
autovacuum_work_mem = -1                # min 1MB, or -1 to use maintenance_work_mem
max_wal_size = 8GB
```

In order to be accessed all user, setting below.

```bash
echo 'host    all             all             0.0.0.0/0               md5' >> /etc/postgresql/16/main/pg_hba.conf
```

To protect network.

```bash
echo 'host    all             all             172.128.128.0/24        md5' >> /etc/postgresql/16/main/pg_hba.conf
```

### Create Database

( Host )

```bash
sudo su postgres
createdb --encoding=UTF8 --locale=ja_JP.utf8 --template=template0 --port 5432 testdb
```

( Docker )

```bash
sudo docker exec --user=postgres postgres createdb --encoding=UTF8 --locale=ja_JP.utf8 --template=template0 --port 5432 testdb
```

### Schema Import/Dump

##### Import schema

( Host )

```bash
cd ~
git clone https://github.com/kazukingh01/kkpsgre.git
cp ~/kkpsgre/test/schema.psgre.sql /home/share/
sudo su postgres
psql -U postgres -d testdb -f /home/share/schema.psgre.sql
```

( Docker )

```bash
cd ~
git clone https://github.com/kazukingh01/kkpsgre.git
cp ~/kkpsgre/test/schema.psgre.sql /home/share/
sudo docker exec --user=postgres postgres psql -U postgres -p 5432 -d testdb -f /home/share/schema.psgre.sql 
```

##### Dump Schema

( Host )

```bash
sudo su postgres
cd ~
pg_dump -U postgres --port 5432 -d testdb -s > ~/schema.psgre.sql
```

( Docker )

```bash
sudo docker exec --user=postgres postgres pg_dump -U postgres -d testdb -s > ~/schema.psgre.sql
```

### Database Backup/Restore

##### Backup

( Host )

```bash
sudo su postgres
cd ~
pg_dump -U postgres -Fc testdb > ~/db_`date "+%Y%m%d"`.dump
```

( Docker )

```bash
sudo docker exec --user=postgres postgres pg_dump -U postgres -Fc testdb > ~/db_`date "+%Y%m%d"`.dump
```

##### Restore

( Host )

```bash
sudo su postgres
cd ~
dropdb testdb
createdb --encoding=UTF8 --locale=ja_JP.utf8 --template=template0 --port 5432 testdb
pg_restore -d testdb /home/share/db_YYYYMMDD.dump
```

( Docker )

```bash
sudo docker exec --user=postgres postgres dropdb testdb
sudo docker exec --user=postgres postgres createdb --encoding=UTF8 --locale=ja_JP.utf8 --template=template0 --port 5432 testdb
sudo docker exec --user=postgres postgres pg_restore -d testdb /home/share/db_YYYYMMDD.dump
```

### Table Backup/Restore

##### Backup

( Host )

```bash
sudo su postgres
cd ~
pg_dump -U postgres -t testtable -Fc testdb > ~/testtable.dump
```

( Docker )

```bash
sudo docker exec --user=postgres postgres pg_dump -U postgres -t testtable -Fc testdb > ~/testtable.dump
```

##### Restore

Don't write "-t testtable" option so that creating index doesn't run.

( Host )

```bash
sudo su postgres
cd ~
psql -U postgres -d testdb --port 5432 -c "DROP TABLE testtable CASCADE;"
pg_restore -U postgres -d testdb -Fc /home/share/testtable.dump
```

( Docker )

```bash
sudo docker exec --user=postgres postgres psql       -U postgres -d testdb --port 5432 -c "DROP TABLE testtable CASCADE;"
sudo docker exec --user=postgres postgres pg_restore -U postgres -d testdb -Fc /home/share/testtable.dump
```

# MySQL

### Install ( Docker Hub Base )

Docker Hub: https://hub.docker.com/_/mysql

```bash
MYSQL_VER="8.0.39-debian"
echo "FROM mysql:${MYSQL_VER}" > ~/Dockerfile
echo "RUN apt-get update" >> ~/Dockerfile
echo "RUN apt-get install -y locales" >> ~/Dockerfile
echo "RUN rm -rf /var/lib/apt/lists/*" >> ~/Dockerfile
echo "RUN echo "ja_JP.UTF-8 UTF-8" > /etc/locale.gen" >> ~/Dockerfile
echo "RUN locale-gen ja_JP.UTF-8" >> ~/Dockerfile
echo "ENV LC_ALL=ja_JP.UTF-8" >> ~/Dockerfile
echo "RUN echo '[mysqld]'                            >  /etc/mysql/conf.d/charset.cnf" >> ~/Dockerfile
echo "RUN echo 'character-set-server=utf8mb4'        >> /etc/mysql/conf.d/charset.cnf" >> ~/Dockerfile
echo "RUN echo 'collation-server=utf8mb4_general_ci' >> /etc/mysql/conf.d/charset.cnf" >> ~/Dockerfile
echo "RUN echo '[mysql]'                             >> /etc/mysql/conf.d/charset.cnf" >> ~/Dockerfile
echo "RUN echo 'default-character-set=utf8mb4'       >> /etc/mysql/conf.d/charset.cnf" >> ~/Dockerfile
echo "RUN echo '[client]'                            >> /etc/mysql/conf.d/charset.cnf" >> ~/Dockerfile
echo "RUN echo 'default-character-set=utf8mb4'       >> /etc/mysql/conf.d/charset.cnf" >> ~/Dockerfile
sudo docker image build -t mysql:${MYSQL_VER}.jp .
sudo mkdir -p /var/local/mysql
sudo docker run --name mysql \
    -e MYSQL_ROOT_PASSWORD=mysql \
    -e MYSQL_USER=mysql \
    -e MYSQL_PASSWORD=mysql \
    -e MYSQL_DATABASE=testdb \
    -e MYSQL_PORT=3306 \
    -e TZ=Asia/Tokyo \
    -v /var/local/mysql:/var/lib/mysql \
    -v /home/share:/home/share \
    -p 63306:3306 \
    --shm-size=4g \
    -d mysql:${MYSQL_VER}.jp
```

### Install TiDB ( Host Base )

**SSH login must be applied to root user of all node**. 

```bash
sudo apt update && sudo apt install -y curl
curl --proto '=https' --tlsv1.2 -sSf https://tiup-mirrors.pingcap.com/install.sh | sh
source ~/.bashrc
tiup cluster
tiup update --self && tiup update cluster
```

edit ```/etc/ssh/sshd_config``` below.

```diff:/etc/ssh/sshd_config
- #MaxSessions 10
+ MaxSessions 20
```

```bash
sudo /etc/init.d/ssh restart
```

```bash
sudo apt update && sudo apt install -y numactl

sudo bash -c "echo \"vm.swappiness = 0\" >> /etc/sysctl.conf"
sudo bash -c "echo \"fs.file-max = 1000000\" >> /etc/sysctl.conf"
sudo bash -c "echo \"net.core.somaxconn = 32768\" >> /etc/sysctl.conf"
sudo bash -c "echo \"net.ipv4.tcp_tw_recycle = 0\" >> /etc/sysctl.conf"
sudo bash -c "echo \"net.ipv4.tcp_syncookies = 0\" >> /etc/sysctl.conf"
sudo bash -c "echo \"vm.overcommit_memory = 1\" >> /etc/sysctl.conf"
sudo sysctl -p

sudo touch /etc/rc.local
sudo chmod 700 /etc/rc.local
sudo bash -c "echo \#\!/bin/bash >> /etc/rc.local"
sudo bash -c "echo \"swapoff -a\" >> /etc/rc.local"
sudo bash -c "echo \"echo never > /sys/kernel/mm/transparent_hugepage/enabled\" >> /etc/rc.local"
sudo bash -c "echo \"echo never > /sys/kernel/mm/transparent_hugepage/defrag\" >> /etc/rc.local"
sudo bash -c "echo \"echo none  > /sys/block/vda/queue/scheduler\" >> /etc/rc.local"
sudo systemctl restart rc-local.service

sudo bash -c "echo \"tidb           soft    nofile          1000000\" >> /etc/security/limits.conf"
sudo bash -c "echo \"tidb           hard    nofile          1000000\" >> /etc/security/limits.conf"
sudo bash -c "echo \"tidb           soft    stack           32768\" >> /etc/security/limits.conf"
sudo bash -c "echo \"tidb           hard    stack           32768\" >> /etc/security/limits.conf"
```

```bash
sudo vi /etc/fstab
```

```diff:/etc/fstab
-UUID=aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa /               ext4    errors=remount-ro 0       1
+UUID=aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa /               ext4    nodelalloc,noatime,errors=remount-ro 0       1
```

create ```~/topo.yml``` file.

```bash:~/topo.yml
# # Global variables are applied to all deployments and used as the default value of
# # the deployments if a specific deployment value is missing.
global:
 user: "tidb"
 ssh_port: 22
 deploy_dir: "/var/local/tidb-deploy"
 data_dir: "/var/local/tidb-data"

# # Monitored variables are applied to all the machines.
monitored:
 node_exporter_port: 9100
 blackbox_exporter_port: 9115

server_configs:
 tidb:
   instance.tidb_slow_log_threshold: 300
 tikv:
   readpool.storage.use-unified-pool: false
   readpool.coprocessor.use-unified-pool: true
 pd:
   replication.enable-placement-rules: true
   replication.location-labels: ["host"]
#  tiflash:
#    logger.level: "info"
#    profiles.default.max_memory_usage: 0.1
#    profiles.default.max_memory_usage_for_all_queries: 0.1

pd_servers:
 - host: 192.168.10.1

tidb_servers:
 - host: 192.168.10.1
   port: 4000

tikv_servers:
 - host: 192.168.10.1
   port: 20160
   status_port: 20180
   config:
     server.labels: { host: "host-1" }

 - host: 192.168.10.2
   port: 20161
   status_port: 20181
   config:
     server.labels: { host: "host-2" }

# tiflash_servers:
#  - host: 192.168.10.2

monitoring_servers:
 - host: 192.168.10.2

# grafana_servers:
#  - host: 192.168.10.2
```

Create cluster and initialize.

```bash
tiup cluster deploy <cluster_name> v8.2.0 ~/topo.yml --user root -i ~/.ssh/id_rsa
tiup cluster start <cluster_name> --init
```

test mysql client.

```bash
sudo apt update && sudo apt-get install -y mysql-client
MYSQLPASS="AAAAAAAAAAAAAAA"
mysql -h 192.168.10.1 -P 4000 -u root --password=${MYSQLPASS}
# SHOW GLOBAL VARIABLES LIKE 'tidb_auto_analyze_partition_batch_size';
# SET GLOBAL tidb_auto_analyze_partition_batch_size = 16;
```

If you want to remove it, type follow.

```bash
tiup cluster destroy <cluster_name>
```

### Crontab ( TiDB )

```bash
echo "PATH=/home/ubuntu/.tiup/bin:/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin" | sudo tee -a /etc/crontab > /dev/null
echo "0   0   * * *   ubuntu  tiup cluster restart -y <cluster_name>" | sudo tee -a /etc/crontab > /dev/null
sudo /etc/init.d/cron restart
```

### Create Database

( Host )

```bash
# mysql --password=mysql -e "DROP DATABASE testdb;"
mysql --password=mysql -e "CREATE DATABASE testdb;"
```

( Docker )

```bash
# sudo docker exec mysql mysql --password=mysql -e "DROP DATABASE testdb;"
sudo docker exec mysql mysql --password=mysql -e "CREATE DATABASE testdb;"
```

### Schema Import/Dump

##### Import schema

( Host )

```bash
cd ~
git clone https://github.com/kazukingh01/kkpsgre.git
cp ~/kkpsgre/test/schema.mysql.sql /home/share/
mysql --password=mysql --database=testdb < /home/share/schema.mysql.sql
```

( Docker )

```bash
cd ~
git clone https://github.com/kazukingh01/kkpsgre.git
cp ~/kkpsgre/test/schema.mysql.sql /home/share/
sudo docker exec mysql /bin/sh -c "mysql --password=mysql --database=testdb < /home/share/schema.mysql.sql"
```

##### Dump Schema

( Host )

```bash
mysql mysqldump --password=mysql --no-data testdb > ~/schema.mysql.sql
```

( Docker )

```bash
sudo docker exec mysql mysqldump --password=mysql --no-data testdb > ~/schema.mysql.sql
```

# MongoDB

https://www.mongodb.com/docs/

### Install ( Host Base ) on Ubuntu:22.04

```bash
sudo apt-get install gnupg curl
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt-get update
sudo apt-get install -y mongodb-org=7.0.14 mongodb-org-database=7.0.14 mongodb-org-server=7.0.14 mongodb-org-mongos=7.0.14 mongodb-org-tools=7.0.14 # not found mongodb-mongosh=7.0.14
sudo apt-get install -y mongodb-mongosh
sudo systemctl start mongod
sudo systemctl daemon-reload
sudo systemctl status mongod
sudo systemctl enable mongod
sudo systemctl restart mongod
# To create user & password. Initially, there is no root user and password.
PASSWORD=`openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 16`
echo ${PASSWORD} > ~/passmongo.txt
sudo chmod 444 ~/passmongo.txt
sudo chown root:root ~/passmongo.txt
mongosh admin --eval "db.createUser({user: 'admin', pwd: '$PASSWORD', roles: [{role: 'root', db: 'admin'}]})"
sudo vi /etc/mongod.conf
```

```diff
+security:
+  authorization: enabled
net:
-  port: 27017
-  bindIp: 127.0.0.1
+  port: XXXXX
+  bindIp: 0.0.0.0

storage:
  dbPath: /var/lib/mongodb
+  wiredTiger:
+    engineConfig:
+      cacheSizeGB: 6
```

Set parameters to modify performance (Maybe...)

```bash
sudo bash -c "echo \"vm.max_map_count = 262144\" >> /etc/sysctl.conf"
sudo bash -c "echo \"vm.swappiness = 0\" >> /etc/sysctl.conf"
sudo bash -c "echo \"fs.file-max = 1000000\" >> /etc/sysctl.conf"
sudo bash -c "echo \"net.core.somaxconn = 32768\" >> /etc/sysctl.conf"
sudo bash -c "echo \"vm.overcommit_memory = 1\" >> /etc/sysctl.conf"
sudo sysctl -p

sudo touch /etc/rc.local
sudo chmod 700 /etc/rc.local
sudo bash -c "echo \#\!/bin/bash >> /etc/rc.local"
sudo bash -c "echo \"swapoff -a\" >> /etc/rc.local"
sudo bash -c "echo \"echo never > /sys/kernel/mm/transparent_hugepage/enabled\" >> /etc/rc.local"
sudo bash -c "echo \"echo never > /sys/kernel/mm/transparent_hugepage/defrag\" >> /etc/rc.local"
sudo bash -c "echo \"echo none  > /sys/block/vda/queue/scheduler\" >> /etc/rc.local"
sudo systemctl restart rc-local.service

sudo bash -c "echo \"mongodb        soft    nofile          1000000\" >> /etc/security/limits.conf"
sudo bash -c "echo \"mongodb        hard    nofile          1000000\" >> /etc/security/limits.conf"
sudo bash -c "echo \"mongodb        soft    stack           32768\" >> /etc/security/limits.conf"
sudo bash -c "echo \"mongodb        hard    stack           32768\" >> /etc/security/limits.conf"

sudo systemctl restart mongod
```

### Create Collection

There is no database.

( Host )

```bash
# mongosh admin -u "admin" -p `cat ~/passmongo.txt` --port 27017 --eval "db.getSiblingDB("test").myCollection.drop()"
mongosh admin -u "admin" -p `cat ~/passmongo.txt` --port 27017 --eval 'db.getSiblingDB("test").createCollection("myCollection")'
# mongosh admin -u "admin" -p `cat ~/passmongo.txt` --port 27017 --eval 'db.getSiblingDB("test").createCollection("myCollection", { timeseries: {timeField: "unixtime", metaField: "symbol", granularity: "seconds" }})'
```

# Migration

### MySQL to TiDB

see: https://docs.pingcap.com/tidb/stable/migrate-from-sql-files-to-tidb

```bash
# ALTER TABLE binance_executions TRUNCATE PARTITION binance_executions_202012;
sudo apt update && sudo apt install -y curl
curl --proto '=https' --tlsv1.2 -sSf https://tiup-mirrors.pingcap.com/install.sh | sh
source ~/.bashrc
tiup cluster
tiup update --self && tiup update cluster
tiup install dumpling dm tidb-lightning
tiup dumpling -u root -P 63306 -h 127.0.0.1 --filetype sql -t 8 -o ./output/ -r 200000 -F 256MiB --tables-list trade.binance_executions -p mysql --no-schemas
nohup tiup tidb-lightning -config tidb-lightning.toml > nohup.out 2>&1 &

tiup dumpling -u root -P 63306 -h 127.0.0.1 -p mysql -o ./output/ --filetype csv --sql 'select * from `trade`.`binance_executions` where unixtime >= 1612137600 and unixtime < 1614556800;' -F 256MiB --output-filename-template 'trade.binance_executions.{{.Index}}' --csv-separator ',' --csv-delimiter ''

nohup tiup tidb-lightning -config tidb-lightning.toml > nohup.out 2>&1 &

```

```toml
[lightning]
# Log
level = "info"
file = "tidb-lightning.log"

[tikv-importer]
# "local": Default. The local backend is used to import large volumes of data (around or more than 1 TiB). During the import, the target TiDB cluster cannot provide any service.
# "tidb": The "tidb" backend can also be used to import small volumes of data (less than 1 TiB). During the import, the target TiDB cluster can provide service normally. For the information about backend mode, refer to https://docs.pingcap.com/tidb/stable/tidb-lightning-backends.

backend = "tidb"
# Sets the temporary storage directory for the sorted key-value files. The directory must be empty, and the storage space must be greater than the size of the dataset to be imported. For better import performance, it is recommended to use a directory different from `data-source-dir` and use flash storage and exclusive I/O for the directory.
sorted-kv-dir = "/home/ubuntu/tmp/"

[mydumper]
# Directory of the data source
data-source-dir = "/home/ubuntu/output/" # Local or S3 path, such as 's3://my-bucket/sql-backup'
no-schema = true
strict-format = false # not so change between on and off
#max-region-size = "64MiB"

[mydumper.csv]
# Field separator of the CSV file. Must not be empty. If the source file contains fields that are not string or numeric, such as binary, blob, or bit, it is recommended not to usesimple delimiters such as ",", and use an uncommon character combination like "|+|" instead.
separator = ','
# Delimiter. Can be zero or multiple characters.
delimiter = ''
# Configures whether the CSV file has a table header.
# If this item is set to true, TiDB Lightning uses the first line of the CSV file to parse the corresponding relationship of fields.
header = true
# Configures whether the CSV file contains NULL.
# If this item is set to true, any column of the CSV file cannot be parsed as NULL.
not-null = false
# If `not-null` is set to false (CSV contains NULL),
# The following value is parsed as NULL.
null = '\N'
# Whether to treat the backslash ('\') in the string as an escape character.
backslash-escape = true
# Whether to trim the last separator at the end of each line.
trim-last-separator = false
terminator = '' # If you change strict-format mode, It must be set "\r\n", not '\r\n'

[tidb]
# The information of target cluster
host = "192.168.1.1"                # For example, 172.16.32.1
port = 4000               # For example, 4000
user = "root"         # For example, "root"
password = "XXXXXXXXXXXXX"      # For example, "rootroot"
status-port = 10080  # During the import process, TiDB Lightning needs to obtain table schema information from the "Status Port" of TiDB, such as 10080.
pd-addr = "192.168.1.1:2379"     # The address of the cluster's PD. TiDB Lightning obtains some information through PD, such as 172.16.31.3:2379. When backend = "local", you must correctly specify status-port and pd-addr. Otherwise, the import will encounter errors.

[cron]
# Duration between which an import progress is printed to the log.
log-progress = "1m"
```