# kkpsgre

Dataframe interface for PostgreSQL

# PostgreSQL

There are 3 options.

- Create database by using docker (use docker hub)
- Create database by using docker (manually install in ubuntu) 
- Create database on host server

### Install ( Docker Hub Base )

```bash
POSTGRESQL_VER="16.3"
echo "FROM postgres:${POSTGRESQL_VER}" > ~/Dockerfile
echo "RUN apt-get update" >> ~/Dockerfile
echo "RUN apt-get install -y locales" >> ~/Dockerfile
echo "RUN rm -rf /var/lib/apt/lists/*" >> ~/Dockerfile
echo "RUN localedef -i ja_JP -c -f UTF-8 -A /usr/share/locale/locale.alias ja_JP.UTF-8" >> ~/Dockerfile
echo "ENV LANG ja_JP.utf8" >> ~/Dockerfile
sudo docker image build -t postgres:${POSTGRESQL_VER}.jp .
sudo mkdir -p /var/local/postgresql/data # This case 
sudo docker run --name postgres \
    -e POSTGRES_PASSWORD=postgres \
    -e POSTGRES_INITDB_ARGS="--encoding=UTF8 --locale=ja_JP.utf8" \
    -e TZ=Asia/Tokyo \
    -v /var/local/postgresql/data:/var/lib/postgresql/data \
    -v /home/share:/home/share \
    -p 65432:5432 \
    --shm-size=4g \
    -d postgres:${POSTGRESQL_VER}.jp
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
initdb -D /var/lib/postgresql/data -E UTF8
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

##### Config for connection

In order to be accessed all user, setting below.

```bash
echo 'host    all             all             0.0.0.0/0               md5' >> /etc/postgresql/16/main/pg_hba.conf
```

To protect network.

```bash
echo 'host    all             all             172.128.128.0/24        md5' >> /etc/postgresql/16/main/pg_hba.conf
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
initdb -D /var/lib/postgresql/data -E UTF8
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
