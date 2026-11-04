from basedatos.migraciones import ejecutar

from app.modelos import Base

ejecutar(Base.metadata, "auth")
