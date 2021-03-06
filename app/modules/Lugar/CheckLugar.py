# -*- coding: utf-8 -*-
from app.config import db_sql
from datetime import datetime
from app.models import Lugar, Usuario, Registro, Detalle_registro, \
                       Lugares_Usuarios


class CheckLugar(object):
    """
    Clase que encapsula el manejo de entradas y salidas de un Lugar.
    :param id_lugar: id del lugar en donde se quiere registrar el evento
    :type id_lugar: int
    :param key: Llave para verificar si el acceso al lugar es válido
    :type key: string
    """
    def __init__(self, id_lugar, key=None, usuario=None):
        self.id_lugar = int(id_lugar)
        self.key = str(key)
        self.lugar = None
        self.usuario = usuario
        self.lugar_activo = None
        self.registro_entrada = None
        self.obten_lugar()

    def set_usuario(self, usuario):
        """
        Configura un usuario para después ser usado por otros métodos
        :param usuario:
        :type usuario: app.models.Usuario
        """
        self.usuario = usuario

    def obten_lugar(self):
        """
        Si existe un Lugar con ese id y esa llave, entonces guarda en
        self.lugar el objeto Lugar y lo retorna. Si no existe el lugar entonces
        guardará y retornará None.
        :return: app.models.Lugar
        """
        query = db_sql.session.query(Lugar.id, Lugar.nombre).filter(
            (Lugar.id == self.id_lugar) & (Lugar.key == str(self.key))
        )
        if query.count() > 0:
            self.lugar = query.first()
        else:
            self.lugar = None
        return self.lugar

    def lugar_valido(self):
        """
        Retorna si ya está seteado un lugar válido en el objeto self o no.
        :return: bool
        """
        return self.lugar is not None

    def obten_lugar_activo(self):
        """
        Obtiene el lugar donde el usuario guardado en self.usuario está activo.
        En caso de que no tenga un lugar activo retornará None.
        En caso de que no exista un usuario en self.usuario arrojará una
        excepción
        :return: app.models.Registro
        :raises: ValueError
        """
        if self.lugar_activo is None:
            if self.usuario is None:
                raise ValueError("self.usuario no ha sido definido, primero llama \
                                  a self.set_usuario")
            else:
                lugar_activo = db_sql.session.query(Registro).filter(
                    (Registro.id_usuario == self.usuario.id) &
                    (Registro.fecha_hora_salida.is_(None))
                )
                if(lugar_activo.count() > 0):
                    self.lugar_activo = lugar_activo.first()
                else:
                    self.lugar_activo = None
                return self.lugar_activo
        else:
            return self.lugar_activo

    def registra_entrada(self):
        """
        Registra la entrada del usuario guardado en self.usuario en el lugar
        self.lugar
        En caso de que no exista un usuario guardado en self.usuario o un lugar
        guardado en self.lugar arrojará una excepción.
        :raises: ValueError
        """
        if self.usuario is None:
            raise ValueError("self.usuario no ha sido definido, primero llama \
                              a self.set_usuario")
        elif self.lugar is None:
            raise ValueError("self.lugar no ha sido definido, primero llama \
                              a self.obten_lugar")
        else:
            self.obten_lugar_activo()
            if self.lugar_activo is None:
                entrada = Registro(id_usuario=self.usuario.id,
                                   id_lugar=self.lugar.id)
                db_sql.session.add(entrada)
                db_sql.session.commit()
                self.registro_entrada = entrada
                r_olvidados = db_sql.session.query(Detalle_registro).filter(
                    Detalle_registro.fecha_hora_entrega.is_(None)
                ).join(Registro.detalles_registro).filter(
                    (Registro.fecha_hora_salida.isnot(None)) &
                    (Registro.id_usuario == self.usuario.id) &
                    (Registro.id_lugar == self.lugar.id)
                )
                if(r_olvidados.count()):
                    recurso_olvidado = r_olvidados.first()
                    recurso_olvidado.id_registro_salida = entrada.id
                    db_sql.session.commit()
            else:
                # TODO sólo permite hacer entradas extras si la entrada previa
                # fue realizada en el lugar padre de este lugar
                raise ValueError("El usuario ya está activo en otro lugar")

    def registra_salida(self):
        """
        Registra la salida del usuario guardado en self.usuario en el lugar
        self.lugar_activo
        En caso de que no exista un lugar guardado en self.lugar_activo
        arrojará una excepción.
        :raises: ValueError
        """
        if self.lugar_activo is None:
            raise ValueError("self.lugar_activo no ha sido definido, primero \
                              llama a self.obten_lugar_activo")
        else:
            self.lugar_activo.fecha_hora_salida = datetime.utcnow()
            db_sql.session.commit()

    def computadora_activa(self):
        """
        Retorna True si existe una computadora activa asociada al usuario
        guardado en self.usuario
        En caso de que no exista un usuario guardado en self.usuario o un lugar
        guardado en self.lugar arrojará una excepción.
        :return: bool
        :raises: ValueError
        """
        if self.usuario is None:
            raise ValueError("self.usuario no ha sido definido, primero llama \
                              a self.set_usuario")
        else:
            c_activa = db_sql.session.query(Detalle_registro.id).filter(
                (Detalle_registro.fecha_hora_toma.isnot(None)) &
                (Detalle_registro.fecha_hora_entrega.is_(None))
            ).join(Registro.detalles_registro).filter(
                (Registro.id_usuario == self.usuario.id) &
                (Registro.fecha_hora_salida.is_(None))
            )
            return c_activa.count() > 0

    def valida_salida(self):
        """
        Valida que se pueda crear una salida para el usuario guardado en
        self.usuario del lugar guardado en self.lugar_activo
        :return: bool, {:text: string, :category: string}
        """
        if(self.lugar_activo.id_lugar == int(self.id_lugar)):
            # if(self.computadora_activa()):
            #    return False, {'text': u'Tienes una computadora sin entregar',
            #                    'category': 'warning'}
            # else:
            self.registra_salida()
            return True, {'text': u'Usuario con código: ' +
                          self.usuario.codigo + u' salió de ' +
                          self.lugar.nombre,
                          'category': 'success'}
        else:
            # TODO verificar si el lugar al que quiere entrar es "hijo" del
            # lugar donde se encuentra activo
            return False, {'text': u'Tienes una entrada activa en otro lugar',
                           'category': 'warning'}

    def verifica_acceso(self):
        """
        Verifica si el usuario guardado en self.usuario tiene acceso en el
        lugar self.lugar
        En caso de que no exista un usuario guardado en self.usuario o un lugar
        guardado en self.lugar arrojará una excepción.
        :raises: ValueError
        """
        if self.usuario is None:
            raise ValueError("self.usuario no ha sido definido, primero llama \
                              a self.set_usuario")
        elif self.lugar is None:
            raise ValueError("self.lugar no ha sido definido, primero llama \
                              a self.obten_lugar")
        acceso = db_sql.session.query(Lugares_Usuarios).filter(
            (Lugares_Usuarios.id_lugar == self.lugar.id) &
            (Lugares_Usuarios.id_usuario == self.usuario.id)
        )
        return acceso.count() > 0

    def valida_entrada_salida_lugar(self):
        """
        Valida que se pueda crear una entrada para el usuario guardado en
        self.usuario del lugar guardado en self.lugar_activo
        :return: bool, {:text: string, :category: string}
        """
        if(self.verifica_acceso()):
            self.lugar_activo = self.obten_lugar_activo()
            if(self.lugar_activo is None):
                self.registra_entrada()
                return True, {'text': u'Usuario con código: ' +
                              self.usuario.codigo + u' entró a ' +
                              self.lugar.nombre,
                              'category': 'success'}
            else:
                return self.valida_salida()
        else:
            return False, {'text': u'El usuario: ' + self.usuario.codigo
                           + u' no tiene acceso a ' + self.lugar.nombre,
                           'category': 'warning'}

    def usuario_valido(self, codigo, nip):
        """
        Valida que exista un usuario que cumpla con el par codigo / nip
        :param codigo: El código del usuario
        :type codigo: string
        :param nip: El nip del usuario
        :type nip: string
        :return: bool, {:text: string, :category: string}
        """
        query = db_sql.session.query(Usuario).filter(
            (Usuario.codigo == codigo)
        )
        if(query.count() > 0):
            usuario = query.first()
            if(usuario.nip == nip):
                self.usuario = usuario
                return True, {}
            else:
                return False, {'text': u'Error en el nip del usuario',
                               'category': 'warning'}
        else:
            return False, {'text': u'No existe un usuario con el código: ' +
                           str(codigo),
                           'category': 'warning'}

    def valida_formulario(self, formulario):
        codigo = formulario.codigo.data
        nip = formulario.nip.data
        usuario_valido, res = self.usuario_valido(codigo, nip)
        if(usuario_valido):
            entrada_salida_valida, res = self.valida_entrada_salida_lugar()
        return res
