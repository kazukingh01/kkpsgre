# Sharding

Setting is below.

|                      | server1 | server2 | server3 |
| ----                 | ----    | ----    | ----    |
| Primary or Secondary | shard1  | shard2  | shard3  | 
| Primary or Secondary | shard2  | shard3  | shard1  | 
| Arbiter              | shard3  | shard1  | shard2  | 

### ENV

```bash
PORTCF=44415
PORTS1=44417
PORTS2=44418
PORTS3=44419
PORTMS=44400
```

### Firewall

```bash
sudo ufw allow from 172.128.128.0/24 to any port ${PORTCF} # Config
sudo ufw allow from 172.128.128.0/24 to any port ${PORTS1} # Shard1
sudo ufw allow from 172.128.128.0/24 to any port ${PORTS2} # Shard2
sudo ufw allow from 172.128.128.0/24 to any port ${PORTS3} # Shard3
sudo ufw allow ${PORTMS} # This is only for mongos server
sudo ufw reload
sudo ufw status
```

### Key Setting to connect servers each other.

```bash
openssl rand -base64 756 > ~/mongoKey.txt
sudo mv ~/mongoKey.txt /etc/mongoKey.txt
sudo chown mongodb:mongodb /etc/mongoKey.txt
sudo chmod 400 /etc/mongoKey.txt
```

### Create directories

If you want to create N sharding, you mush create /var/lib/mongodb/shard1 ~ /var/lib/mongodb/shardN.

```bash
sudo cp /etc/mongod.conf /etc/mongod.conf.bk`date +%Y%m%d`
sudo systemctl stop mongod
sudo systemctl disable mongod
sudo systemctl mask mongod
sudo rm -rf /var/lib/mongodb
sudo mkdir -p /var/lib/mongodb/shard1
sudo mkdir -p /var/lib/mongodb/shard2
sudo mkdir -p /var/lib/mongodb/shard3
sudo mkdir -p /var/lib/mongodb/config
sudo chown -R mongodb:mongodb /var/lib/mongodb
```

### ShardServer config

```bash
sudo rm /etc/mongod.shard1.conf
sudo touch /etc/mongod.shard1.conf
sudo bash -c "echo \"security:\"                           >> /etc/mongod.shard1.conf"
sudo bash -c "echo \"  authorization: enabled\"            >> /etc/mongod.shard1.conf"
sudo bash -c "echo \"  keyFile: /etc/mongoKey.txt\"        >> /etc/mongod.shard1.conf"
sudo bash -c "echo \"storage:\"                            >> /etc/mongod.shard1.conf"
sudo bash -c "echo \"  dbPath: /var/lib/mongodb/shard1\"   >> /etc/mongod.shard1.conf"
sudo bash -c "echo \"systemLog:\"                          >> /etc/mongod.shard1.conf"
sudo bash -c "echo \"  destination: file\"                 >> /etc/mongod.shard1.conf"
sudo bash -c "echo \"  logAppend: true\"                   >> /etc/mongod.shard1.conf"
sudo bash -c "echo \"  path: /var/log/mongodb/shard1.log\" >> /etc/mongod.shard1.conf"
sudo bash -c "echo \"net:\"                                >> /etc/mongod.shard1.conf"
sudo bash -c "echo \"  port: $PORTS1\"                     >> /etc/mongod.shard1.conf"
sudo bash -c "echo \"  bindIp: 0.0.0.0\"                   >> /etc/mongod.shard1.conf"
sudo bash -c "echo \"processManagement:\"                  >> /etc/mongod.shard1.conf"
sudo bash -c "echo \"  timeZoneInfo: /usr/share/zoneinfo\" >> /etc/mongod.shard1.conf"
sudo bash -c "echo \"replication:\"                        >> /etc/mongod.shard1.conf"
sudo bash -c "echo \"  replSetName: "shard1ReplSet"\"      >> /etc/mongod.shard1.conf"
sudo bash -c "echo \"sharding:\"                           >> /etc/mongod.shard1.conf"
sudo bash -c "echo \"  clusterRole: shardsvr\"             >> /etc/mongod.shard1.conf"
sudo bash -c "echo \"processManagement:\"                  >> /etc/mongod.shard1.conf"
sudo bash -c "echo \"  fork: true\"                        >> /etc/mongod.shard1.conf"
# Repeat to create until shardN.config
sudo cp /etc/mongod.shard1.conf /etc/mongod.shard2.conf
sudo cp /etc/mongod.shard1.conf /etc/mongod.shard3.conf
sudo sed -i 's/shard1/shard2/' /etc/mongod.shard2.conf && sudo sed -i "s/$PORTS1/$PORTS2/" /etc/mongod.shard2.conf
sudo sed -i 's/shard1/shard3/' /etc/mongod.shard3.conf && sudo sed -i "s/$PORTS1/$PORTS3/" /etc/mongod.shard3.conf
sudo chown mongodb:mongodb /etc/mongod.shard1.conf
sudo chown mongodb:mongodb /etc/mongod.shard2.conf
sudo chown mongodb:mongodb /etc/mongod.shard3.conf
```

### ConfigServer config

Config server must be same at all server.

```bash
sudo rm /etc/mongod.config.conf
sudo touch /etc/mongod.config.conf
sudo bash -c "echo \"security:\"                           >> /etc/mongod.config.conf"
sudo bash -c "echo \"  authorization: enabled\"            >> /etc/mongod.config.conf"
sudo bash -c "echo \"  keyFile: /etc/mongoKey.txt\"        >> /etc/mongod.config.conf"
sudo bash -c "echo \"storage:\"                            >> /etc/mongod.config.conf"
sudo bash -c "echo \"  dbPath: /var/lib/mongodb/config\"   >> /etc/mongod.config.conf"
sudo bash -c "echo \"systemLog:\"                          >> /etc/mongod.config.conf"
sudo bash -c "echo \"  destination: file\"                 >> /etc/mongod.config.conf"
sudo bash -c "echo \"  logAppend: true\"                   >> /etc/mongod.config.conf"
sudo bash -c "echo \"  path: /var/log/mongodb/config.log\" >> /etc/mongod.config.conf"
sudo bash -c "echo \"net:\"                                >> /etc/mongod.config.conf"
sudo bash -c "echo \"  port: $PORTCF\"                     >> /etc/mongod.config.conf"
sudo bash -c "echo \"  bindIp: 0.0.0.0\"                   >> /etc/mongod.config.conf"
sudo bash -c "echo \"processManagement:\"                  >> /etc/mongod.config.conf"
sudo bash -c "echo \"  timeZoneInfo: /usr/share/zoneinfo\" >> /etc/mongod.config.conf"
sudo bash -c "echo \"replication:\"                        >> /etc/mongod.config.conf"
sudo bash -c "echo \"  replSetName: "configReplSet"\"      >> /etc/mongod.config.conf"
sudo bash -c "echo \"sharding:\"                           >> /etc/mongod.config.conf"
sudo bash -c "echo \"  clusterRole: configsvr\"            >> /etc/mongod.config.conf"
sudo bash -c "echo \"processManagement:\"                  >> /etc/mongod.config.conf"
sudo bash -c "echo \"  fork: true\"                        >> /etc/mongod.config.conf"
sudo chown mongodb:mongodb /etc/mongod.config.conf
```

### Environment for config & Run command

|      | server1                 | server2                 | server3                 |
| ---- | ----                    | ----                    | ----                    |
|      | /etc/mongod.shard1.conf | /etc/mongod.shard1.conf | /etc/mongod.shard1.conf | 
|      | /etc/mongod.shard2.conf | /etc/mongod.shard2.conf | /etc/mongod.shard2.conf | 
|      | /etc/mongod.shard3.conf | /etc/mongod.shard3.conf | /etc/mongod.shard3.conf | 
|      | /etc/mongod.config.conf | /etc/mongod.config.conf | /etc/mongod.config.conf | 

Server1

```bash
sudo -u mongodb mongod --config /etc/mongod.shard1.conf
sudo -u mongodb mongod --config /etc/mongod.shard2.conf
sudo -u mongodb mongod --config /etc/mongod.shard3.conf
sudo -u mongodb mongod --config /etc/mongod.config.conf
```

Server2

```bash
sudo -u mongodb mongod --config /etc/mongod.shard1.conf
sudo -u mongodb mongod --config /etc/mongod.shard2.conf
sudo -u mongodb mongod --config /etc/mongod.shard3.conf
sudo -u mongodb mongod --config /etc/mongod.config.conf
```

Server3

```bash
sudo -u mongodb mongod --config /etc/mongod.shard1.conf
sudo -u mongodb mongod --config /etc/mongod.shard2.conf
sudo -u mongodb mongod --config /etc/mongod.shard3.conf
sudo -u mongodb mongod --config /etc/mongod.config.conf
```

### ConfigServer initialize

Do this only at Server1.

```bash
SV1="172.128.128.10"
SV2="172.128.128.11"
SV3="172.128.128.12"
mongosh --port ${PORTCF} --eval "rs.initiate({_id: 'configReplSet', configsvr: true, members: [{ _id: 0, host: '$SV1:$PORTCF' },{ _id: 1, host: '$SV2:$PORT' },{ _id: 2, host: '$SV3:$PORT' }]})"
```

Check replica set status via rs.status(). A example is below.

```bash
mongosh --port ${PORTCF}
```

```js
configReplSet [direct: primary] admin> rs.status()
{
  set: 'configReplSet',
  date: ISODate('2025-01-11T09:30:21.500Z'),
  ...
  members: [
    {
      _id: 0,
      name: '172.128.128.10:44415',
      health: 1,
      state: 1,
      stateStr: 'PRIMARY',
      ...
    },
    {
      _id: 1,
      name: '172.128.128.11:44415',
      health: 1,
      state: 2,
      stateStr: 'SECONDARY',
      ...
    },
    {
      _id: 2,
      name: '172.128.128.12:44415',
      health: 1,
      state: 2,
      stateStr: 'SECONDARY',
      ...
    }
  ],
  ok: 1,
  ...
```

### ShardServer initialize

Server1

```bash
mongosh --port $PORTS1 --eval \
  "rs.initiate({_id: 'shard1ReplSet', members: [{ _id: 0, host: '$SV1:$PORTS1' },{ _id: 1, host: '$SV2:$PORTS2' },{ _id: 2, host: '$SV3:$PORTS3', arbiterOnly: true }]})"
```

Server2

```bash
mongosh --port $PORTS2 --eval \
  "rs.initiate({_id: 'shard2ReplSet', members: [{ _id: 0, host: '$SV2:$PORTS2' },{ _id: 1, host: '$SV3:$PORTS3' },{ _id: 2, host: '$SV1:$PORTS1', arbiterOnly: true }]})"
```

Server3

```bash
mongosh --port $PORTS3 --eval \
  "rs.initiate({_id: 'shard3ReplSet', members: [{ _id: 0, host: '$SV3:$PORTS3' },{ _id: 1, host: '$SV1:$PORTS1' },{ _id: 2, host: '$SV2:$PORTS2', arbiterOnly: true }]})"
```

### Mongos Config

```bash
sudo rm /etc/mongos.conf
sudo touch /etc/mongos.conf
sudo bash -c "echo \"sharding:\"                                                                    >> /etc/mongos.conf"
sudo bash -c "echo \"  configDB: configReplSet/${SV1}:${PORTCF},${SV2}:${PORTCF},${SV3}:${PORTCF}\" >> /etc/mongos.conf"
sudo bash -c "echo \"net:\"                                                                         >> /etc/mongos.conf"
sudo bash -c "echo \"  port: $PORTMS\"                                                              >> /etc/mongos.conf"
sudo bash -c "echo \"  bindIp: 0.0.0.0\"                                                            >> /etc/mongos.conf"
sudo bash -c "echo \"systemLog:\"                                                                   >> /etc/mongos.conf"
sudo bash -c "echo \"  destination: file\"                                                          >> /etc/mongos.conf"
sudo bash -c "echo \"  logAppend: true\"                                                            >> /etc/mongos.conf"
sudo bash -c "echo \"  path: /var/log/mongodb/mongos.log\"                                          >> /etc/mongos.conf"
sudo bash -c "echo \"processManagement:\"                                                           >> /etc/mongos.conf"
sudo bash -c "echo \"  fork: true\"                                                                 >> /etc/mongos.conf"
```

### Mongos run & set password

```bash
sudo -u mongodb mongos --config /etc/mongos.conf --keyFile /etc/mongoKey.txt # run mongos
PASSWORD=`openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 16`
echo ${PASSWORD} > ~/passmongo.txt
sudo chmod 444 ~/passmongo.txt
sudo chown root:root ~/passmongo.txt
mongosh admin --port $PORTMS --eval "db.createUser({user: 'admin', pwd: '$PASSWORD', roles: [{role: 'root', db: 'admin'}]})"
mongosh admin -u "admin" -p `cat ~/passmongo.txt` --port $PORTMS # test
mongosh admin -u "admin" -p `cat ~/passmongo.txt` --port $PORTMS --eval "db.adminCommand( { setDefaultRWConcern: 1, defaultReadConcern: { 'level': 'local' }, defaultWriteConcern: { 'w': 1 }, writeConcern: { 'w': 1 } })" # This setting for below error. MongoServerError: Cannot add shard1ReplSet/172.128.128.10:44417,172.128.128.11:44417,172.128.128.12:44417 as a shard since the implicit default write concern on this shard is set to {w : 1}, because number of arbiters in the shard's configuration caused the number of writable voting members not to be strictly more than the voting majority. Change the shard configuration or set the cluster-wide write concern using the setDefaultRWConcern command and try again.
mongosh admin -u "admin" -p `cat ~/passmongo.txt` --port $PORTMS --eval "sh.addShard('shard1ReplSet/$SV1:$PORTS1,$SV2:$PORTS1,$SV3:$PORTS1');"
mongosh admin -u "admin" -p `cat ~/passmongo.txt` --port $PORTMS --eval "sh.addShard('shard2ReplSet/$SV1:$PORTS2,$SV2:$PORTS2,$SV3:$PORTS2');"
mongosh admin -u "admin" -p `cat ~/passmongo.txt` --port $PORTMS --eval "sh.addShard('shard3ReplSet/$SV1:$PORTS3,$SV2:$PORTS3,$SV3:$PORTS3');"
mongosh admin -u "admin" -p `cat ~/passmongo.txt` --port $PORTMS --eval "sh.status();"
```

### Enable Database sharding

```bash
mongosh admin -u "admin" -p `cat ~/passmongo.txt` --port $PORTMS --eval 'sh.enableSharding("DBname");'
mongosh admin -u "admin" -p `cat ~/passmongo.txt` --port $PORTMS --eval 'sh.shardCollection("DBname.tablename", {"meta": 1});'
```