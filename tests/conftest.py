import os

import pytest

# Sin cuenta obligatoria (las cuentas y la beta se prueban en test_cuentas.py).
os.environ.setdefault("FUELPATH_ACCESO_LIBRE", "1")
for k in [k for k in os.environ if k.startswith("FUELPATH_CORREO_")]:
    del os.environ[k]                      # nunca mandar correos de verdad desde los tests


@pytest.fixture(autouse=True, scope="session")
def _registro_temporal(tmp_path_factory):
    """El registro y las cuentas de los tests van a una SQLite propia, no a la de /tmp."""
    from fuelpath import acceso, registro
    registro.configurar(str(tmp_path_factory.mktemp("registro") / "registro.sqlite"))
    acceso.olvidar()
    acceso.configurar(activo=False)
