import os
db_user = os.environ.get('DBAAS_USER_NAME', 'POLSHCHAK')
db_password = os.environ.get('DBAAS_USER_PASSWORD', 'Qwer1234')
db_connect = os.environ.get('DBAAS_DEFAULT_CONNECT_DESCRIPTOR', "192.168.56.101:1521/xe")