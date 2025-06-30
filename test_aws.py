import boto3
from botocore.exceptions import NoCredentialsError

# Crear una sesión de cliente de S3
s3 = boto3.client('s3')

# Intentar listar los buckets de S3
try:
    response = s3.list_buckets()
    print("Conexión exitosa a AWS S3")
    print("Buckets disponibles:")
    for bucket in response['Buckets']:
        print(f'- {bucket["Name"]}')
except NoCredentialsError:
    print("Error: No se encontraron las credenciales de AWS.")
except Exception as e:
    print(f"Error al conectar con AWS S3: {str(e)}")
