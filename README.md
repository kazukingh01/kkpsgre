# kkpsgre

Dataframe interface for PostgreSQL

# Database

There are 2 options.

- Create database by using docker 
- Create database on host server

### Install PostgreSQL

#### Host Base

```bash
sudo apt-get update
UBUNTU_CODENAME=`cat /etc/os-release | grep UBUNTU_CODENAME | cut -d '=' -f 2`
echo "deb http://apt.postgresql.org/pub/repos/apt/ ${UBUNTU_CODENAME}-pgdg main" | sudo tee -a /etc/apt/sources.list.d/pgdg.list
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt-get update
sudo apt-get install -y postgresql-16 # check "apt search postgresql"
```

#### Docker Base

```bash
sudo docker pull ubuntu:22.04
sudo docker run -itd -v /home/share:/home/share -p 65432:5432 --name postgres ubuntu:22.04 /bin/sh
sudo docker exec -it postgres /bin/bash
```

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

### Locale setting

```bash
sudo apt-get install -y language-pack-ja
locale -a
# C
# C.utf8
# POSIX
# ja_JP.utf8
```

### DB initialize

```bash
sudo su postgres
cd ~
mkdir /var/lib/postgresql/data
/usr/lib/postgresql/16/bin/initdb -D /var/lib/postgresql/data -E UTF8
```

### Start & Check

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
\q
```

### PostgreSQL password setting

```bash
psql
alter role postgres with password 'postgres';
\q
```

### Config for connection

In order to be accessed all user, setting below.

```bash
echo 'host    all             all             0.0.0.0/0               md5' >> /etc/postgresql/16/main/pg_hba.conf
```

To protect network.

```bash
echo 'host    all             all             172.128.128.0/24        md5' >> /etc/postgresql/16/main/pg_hba.conf
```

### Config for memory

```bash
vi /etc/postgresql/16/main/postgresql.conf
```

```
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

```bash
exit
sudo /etc/init.d/postgresql restart
```

### Docker Save ( If you need )

```bash
exit
sudo docker stop postgres
sudo docker commit postgres postgres:XX.X # save image
sudo docker save postgres:XX.X > postgres_XX.X.tar # export tar
sudo docker rm postgres
```

### Create Database

( for docker )

```bash
sudo docker exec -it postgres /bin/bash
```

```bash
sudo su postgres
cd ~
/usr/lib/postgresql/16/bin/createdb --encoding=UTF8 --locale=ja_JP.utf8 --template=template0 --port 5432 testdb
psql
\l
# postgres=# \l
#                                                        List of databases
#    Name    |  Owner   | Encoding | Locale Provider |   Collate   |    Ctype    | ICU Locale | ICU Rules |   Access privileges
# -----------+----------+----------+-----------------+-------------+-------------+------------+-----------+-----------------------
#  postgres  | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |            |           |
#  template0 | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |            |           | =c/postgres          +
#            |          |          |                 |             |             |            |           | postgres=CTc/postgres
#  template1 | postgres | UTF8     | libc            | en_US.UTF-8 | en_US.UTF-8 |            |           | =c/postgres          +
#            |          |          |                 |             |             |            |           | postgres=CTc/postgres
#  testdb    | postgres | UTF8     | libc            | ja_JP.utf8  | ja_JP.utf8  |            |           |
# (4 rows)
\q
```

### Import schema

#### For Host

```bash
cd ~
git clone https://github.com/kazukingh01/kkpsgre.git
psql -U postgres -d testdb -f ~/kkpsgre/test/schema.sql
```

#### For Docker 

```bash
cd ~
git clone https://github.com/kazukingh01/kkpsgre.git
cp ~/kkpsgre/test/schema.sql /home/share/
sudo docker exec --user=postgres postgres psql -U postgres -d testdb -f /home/share/schema.sql 
```

### Dump Schema

#### For Host 

```bash
sudo su postgres
cd ~
pg_dump -U postgres --port 5432 -d testdb -s > ~/schema.sql
```

#### For Docker 

```bash
sudo docker exec --user=postgres postgres pg_dump -U postgres -d testdb -s > ~/schema.sql
```


### Database Backup/Restore

#### Backup

```bash
sudo docker exec --user=postgres postgres pg_dump -U postgres \
    -t test \
    -Fc testdb > ~/db_`date "+%Y%m%d"`.dump
```

#### Restore

```bash
sudo su postgres
psql testdb -c "DELETE FROM test;"
pg_restore -a -d testdb -t tset -Fc ~/db_`date "+%Y%m%d"`.dump
```