import os
from connection_config import db_connect, db_user, db_password
import time
import random
from flask import Flask, url_for, session, redirect, escape, request, logging, flash
from flask_uploads import UploadSet, IMAGES
# from flask.ext.session import Session
from flask_session import Session
from flask import render_template
from flask_wtf import FlaskForm, Form
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import Form, StringField, TextAreaField, PasswordField, DateField, DateTimeField, RadioField, widgets, SelectMultipleField, validators
from werkzeug.utils import secure_filename
from passlib.hash import sha256_crypt
from functools import wraps
from passlib.hash import md5_crypt
import cx_Oracle
os.environ['NLS_LANG'] = 'American_America.AL32UTF8'
UPLOAD_FOLDER = 'media/med_doc'
ALLOWED_EXTENSIONS = set(['pdf', 'png', 'jpg', 'jpeg', 'gif', 'pdf'])
# db_user = os.environ.get('DBAAS_USER_NAME', 'POLSHCHAK')
# db_password = os.environ.get('DBAAS_USER_PASSWORD', 'Qwer1234')
# db_connect = os.environ.get('DBAAS_DEFAULT_CONNECT_DESCRIPTOR', "192.168.56.101:1521/xe")
images = UploadSet('images', IMAGES)
# SESSION_TYPE = 'cookie'


def create_app(sess):
    app = Flask(__name__)
    app.config.from_object(__name__)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['SESSION_TYPE'] = 'filesystem'
    app.secret_key = 'A0Zr98j/3yXR~XHH!jmN]LWX/,?RT'
    app.debug = True
    sess.init_app(app)
    return app


sess = Session()
app = create_app(sess)

INSERT_USER_VALUES = ('USER_ID', 'EMAIL', 'ROLE_NAME_FK', 'FIRST_NAME', 'SECOND_NAME', 'LAST_NAME', 'BIRTHDAY',
                        'REG_DAY', 'USER_ADDRESS', 'PHONE_NUMBER', 'MED_DOC', 'SPORT_RANK')

INSERT_USER_VALUES_DICT = {item.upper(): None for item in INSERT_USER_VALUES}

USER_DATA_PROC_LIST = (('Admin', 'Coach', 'Client', 'Guest'),
                       ('FILTERSTUFF', 'FILTERSTUFF', 'FILTERCLIENT', 'FILTERGUEST'),
                       )

ROLE_IN_UKR = (('Admin', 'Coach', 'Client', 'Guest'),
               ('Адміністратор', 'Тренер', 'Клієнт', 'Гість'))


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class ValuesDict:
    def __init__(self, *args, **kwargs):
        # do this shit on DATABASE asshole!
        self.user_dict = {}.update(INSERT_USER_VALUES_DICT)
        for name, value in kwargs:
            self.user_dict[name] = value

    def __call__(self, *args, **kwargs):
        return self.user_dict


class InsertGenerator(ValuesDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.table_name = kwargs['table_name']
        self.insert_names_map = kwargs.pop('insert_names_map')

    def generate_insert(self) ->str:
        values = ', '.join((str(self.user_dict[item]) for item in self.insert_names_map))
        params = ', '.join((item for item in self.insert_names_map))
        return "INSERT INTO {0} ({1}) VALUES ({2});".format(self.table_name, params, values)


class UserInsertGenerator(InsertGenerator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs.update({'insert_names_map': INSERT_USER_VALUES}))


class UserCreation:
    def __enter__(self):
        self.__db = cx_Oracle.connect(db_user, db_password, db_connect)
        self.__cursor = self.__db.cursor()
        return self

    def __exit__(self, type=0, value=1, traceback=1):
        self.__cursor.close()
        self.__db.close()

    def get_stuff_data(self, email: str, role_name: str, first_name: str, second_name: str, last_name: str,
                       sport_rank: str, order='email') -> list:
        stuff = []
        try:
            app.logger.info("SQL IS\n" + """SELECT EMAIL, ROLE_NAME, FIRST_NAME, SECOND_NAME, LAST_NAME, SPORT_RANK
                                     FROM TABLE(WORK_PACK.FILTERSTUFF(email_f => '%{0}%',
                                                                        role_name_f => '%{1}%',
                                                                        first_name_f => '%{2}%',
                                                                        second_name_f =>'%{3}%',
                                                                        last_name_f => '%{4}%',
                                                                        sport_rank_f => '%{5}%')) ORDER BY 
                                     {6}""".format(email, role_name, first_name, second_name, last_name, sport_rank,
                                                   order.upper()))
            self.__cursor.execute("""SELECT EMAIL, ROLE_NAME, FIRST_NAME, SECOND_NAME, LAST_NAME, SPORT_RANK
                                     FROM TABLE(WORK_PACK.FILTERSTUFF(email_f => '%{0}%',
                                                                        role_name_f => '%{1}%',
                                                                        first_name_f => '%{2}%',
                                                                        second_name_f =>'%{3}%',
                                                                        last_name_f => '%{4}%',
                                                                        sport_rank_f => '%{5}%')) ORDER BY 
                                     {6}""".format(email, role_name, first_name, second_name, last_name, sport_rank,
                                                   order.upper()))
            stuff = self.__cursor.fetchall()
        except cx_Oracle.DatabaseError:
            flash('ERROR', 'danger')
        return stuff

    def get_client_data(self, email: str, role_name: str, first_name: str, second_name: str, last_name: str,
                        sport_rank: str, order='email') -> list:
        stuff = []
        try:
            self.__cursor.execute("""SELECT EMAIL, ROLE_NAME, FIRST_NAME, SECOND_NAME, LAST_NAME, SPORT_RANK
                                     FROM TABLE(WORK_PACK.FILTERCLIENT(email_f => '%{0}%',
                                                                        role_name_f => '%{1}%',
                                                                        first_name_f => '%{2}%',
                                                                        second_name_f =>'%{3}%',
                                                                        last_name_f => '%{4}%',
                                                                        sport_rank_f => '%{5}%')) ORDER BY 
                                     {6}""".format(email, role_name, first_name, second_name, last_name, sport_rank,
                                                   order.upper()))
            stuff = self.__cursor.fetchall()
        except cx_Oracle.DatabaseError:
            flash('ERROR', 'danger')
        return stuff

    def get_guest_data(self, email: str, role_name: str, first_name: str, second_name: str, last_name: str,
                        sport_rank: str, order='email') -> list:
        stuff = []
        try:
            self.__cursor.execute("""SELECT EMAIL, ROLE_NAME, FIRST_NAME, SECOND_NAME, LAST_NAME, SPORT_RANK
                                     FROM TABLE(WORK_PACK.FILTERGUEST(email_f => '%{0}%',
                                                                        role_name_f => '%{1}%',
                                                                        first_name_f => '%{2}%',
                                                                        second_name_f =>'%{3}%',
                                                                        last_name_f => '%{4}%',
                                                                        sport_rank_f => '%{5}%')) ORDER BY 
                                     {6}""".format(email, role_name, first_name, second_name, last_name, sport_rank,
                                                   order.upper()))
            stuff = self.__cursor.fetchall()
        except cx_Oracle.DatabaseError:
            flash('ERROR', 'danger')
        return stuff

    def get_user_data(self, email: str, role_list: tuple, first_name: str, second_name: str, last_name: str,
                        sport_rank: str, order='email') -> list:
        stuff = []
        if len(role_list) == 0:
            role_list = USER_DATA_PROC_LIST[0]

        query_sample = """SELECT EMAIL, ROLE_NAME, FIRST_NAME, SECOND_NAME, LAST_NAME, SPORT_RANK
                                     FROM TABLE(WORK_PACK.{0}(email_f => '%{1}%',
                                                              role_name_f => '%{2}%',
                                                              first_name_f => '%{3}%',
                                                              second_name_f =>'%{4}%',
                                                              last_name_f => '%{5}%',
                                                              sport_rank_f => '%{6}%'))"""
        complex_query = ' UNION '.join([query_sample.format(USER_DATA_PROC_LIST[1][USER_DATA_PROC_LIST[0].index(role_name)],
                                                            email,
                                                            role_name,
                                                            first_name,
                                                            second_name,
                                                            last_name,
                                                            sport_rank
                                                            ) for role_name in role_list]) + ' ORDER BY ' + order
        try:
            self.__cursor.execute(complex_query)
            stuff = self.__cursor.fetchall()
        except cx_Oracle.DatabaseError:
            flash('ERROR', 'danger')
        return stuff

    def get_team_member_data(self, email: str, role_list: tuple, first_name: str, second_name: str, last_name: str,
                        sport_rank: str, order='email') -> list:
        stuff = []
        if len(role_list) == 0:
            role_list = USER_DATA_PROC_LIST[0]

        query_sample = """SELECT TEAM_NAME, COACH_EMAIL, MEMBER_EMAIL, FIRST_NAME, SECOND_NAME, LAST_NAME, SPORT_RANK
                                     FROM TABLE(WORK_PACK.FILTERTEAMMEMBER(team_name_f => '%{0}%',
                                                                          email_f => '%{1}%',
                                                                          first_name_f => '%{3}%',
                                                                          second_name_f =>'%{4}%',
                                                                          last_name_f => '%{5}%',
                                                                          sport_rank_f => '%{6}%'))"""
        complex_query = ' UNION '.join([query_sample.format(USER_DATA_PROC_LIST[1][USER_DATA_PROC_LIST[0].index(role_name)],
                                                            email,
                                                            role_name,
                                                            first_name,
                                                            second_name,
                                                            last_name,
                                                            sport_rank
                                                            ) for role_name in role_list]) + ' ORDER BY ' + order
        try:
            self.__cursor.execute(complex_query)
            stuff = self.__cursor.fetchall()
        except cx_Oracle.DatabaseError:
            flash('ERROR', 'danger')
        return stuff


    def get_user_login_data(self, login_candidate, password_candidate):
        h_password = ' '
        try:
            h_password = self.__cursor.callfunc("WORK_PACK.GETUSERLOGINDATA", cx_Oracle.STRING, [login_candidate])
        except cx_Oracle.DatabaseError:
            flash('ERROR')
        if sha256_crypt.verify(password_candidate, h_password):
            app.logger.info('PASSWORD MATCHED')
            return True
        else:
            app.logger.info('PASSWORD OR LOGIN NOT MATCHED')
            return False

    def get_user_role(self, login_candidate):
        user_role = 'None'
        try:
            user_role = self.__cursor.callfunc('WORK_PACK.GETUSERROLE', cx_Oracle.STRING, [login_candidate])
        except cx_Oracle.DatabaseError:
            flash('ERROR')
        return user_role

    def get_user_fsl_name(self, login_candidate, role):
        user_fsl = []
        try:
            self.__cursor.execute("""SELECT FIRST_NAME, SECOND_NAME, LAST_NAME FROM "{0}" WHERE 
                                                EMAIL='{1}' """.format(role, login_candidate))
            user_fsl = self.__cursor.fetchone()
        except cx_Oracle.DatabaseError:
            flash('ERROR')
        return user_fsl

    def get_emp(self, email: str) -> tuple:
        stuff = []
        try:
            self.__cursor.execute("""SELECT * FROM TABLE(WORK_PACK.GETEMP('{0}'))""".format(email))
            stuff = self.__cursor.fetchone()
        except cx_Oracle.DatabaseError:
            flash('ERROR', 'danger')
        return stuff

    def get_client(self, email: str) -> tuple:
        stuff = []
        try:
            self.__cursor.execute("""SELECT * FROM TABLE(WORK_PACK.GETCLIENT('{0}'))""".format(email))
            stuff = self.__cursor.fetchone()
        except cx_Oracle.DatabaseError:
            flash('ERROR', 'danger')
        return stuff

    def get_guest(self, email: str) -> tuple:
        stuff = []
        try:
            self.__cursor.execute("""SELECT * FROM TABLE(WORK_PACK.GETGUEST('{0}'))""".format(email))
            stuff = self.__cursor.fetchone()
        except cx_Oracle.DatabaseError:
            flash('ERROR', 'danger')
        return stuff

    def add_user(self, email, password, first_name, second_name, last_name, address, phone, med_doc, sport_rank,
                 birthday):
        try:
            self.__db.commit()
            self.__cursor.callproc('WORK_PACK.REGISTERGUEST', [email, password,
                                                               first_name,
                                                               second_name,
                                                               last_name, address,
                                                               phone, med_doc,
                                                               sport_rank, birthday.isoformat()])
            self.__db.commit()
        except BaseException:
            flash('DB ERROR')
            pass

    def update_user(self, email, role_name, first_name, second_name, last_name, address, phone, med_doc, sport_rank,
                    birthday):
        try:
            self.__db.commit()
            self.__cursor.callproc('WORK_PACK.UPDATEEMP',  [email, role_name,
                                                            first_name,
                                                            second_name,
                                                            last_name, address,
                                                            phone, med_doc,
                                                            sport_rank, birthday])
            self.__db.commit()
        except cx_Oracle.DatabaseError:
            flash('DB ERROR')
            pass


uc = UserCreation()


@app.route('/')
def index():
    return render_template('index.html')


def col_dict(dict_of_params: dict) -> dict:
    res_dict = {}
    for item in dict_of_params:
        res_dict[item.upper()] = dict_of_params[item]
    return res_dict


def allowed_file(file_name):
    return '.' in file_name and file_name.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def register_of_user(dict_of_cols):
    list_of_cols = ['user_id', 'email', 'role_name_fk', 'first_name', 'second_name', 'last_name', 'birthday', 'reg_day',
                    'user_address', 'phone_number', 'med_doc', 'sport_rank', 'password']
    # """%(VALUE)s""" % ({'VALUE': value,})
    # do this shit on DATABASE asshole!
    user_id = random.randint(0, 2147483647)
    connection = cx_Oracle.connect(db_user, db_password, db_connect)
    cur = connection.cursor()
    # try:
    # cur.execute("""SELECT USER_ID FROM "User" WHERE USER_ID=%(_USER_ID)s""" % ({'_USER_ID': user_id}))
    # except
    user_id = random.randint(0, 2147483647)
    cur.commit()
    cur.close()
    connection.close()
    return True


@app.route('/test')
def test_page():
    # """%(VALUE)s""" % ({'VALUE': value,})
    connection = cx_Oracle.connect(db_user, db_password, db_connect)
    cur = connection.cursor()
    # cur.execute("SELECT 'Hello, World from Oracle DB!' FROM DUAL")
    cur.execute("""SELECT * FROM "User" """)
    col = cur.fetchone()[0]
    cur.close()
    connection.close()
    return render_template('test_page.html', info=col[0])


class SimpleForm(Form):
    string_of_files = ['Admin\r\nCoach\r\nClient\r\nGuest\r\n']
    list_of_files = string_of_files[0].split()
    # create a list of value/description tuples
    files = [(x, x) for x in list_of_files]
    example = MultiCheckboxField('Role', choices=files)


class RegisterForm(Form):
    email = StringField('Email', [validators.Length(min=1, max=254)])
    password = PasswordField('Password', [validators.DataRequired(),
                                          validators.EqualTo('confirm_password',
                                                             message='Passwords do not match')])
    confirm_password = PasswordField('Confirm Password')
    first_name = StringField('First Name', [validators.Length(min=1, max=256)])
    second_name = StringField('Second Name', [validators.Length(min=1, max=256)])
    last_name = StringField('Last Name', [validators.Length(min=1, max=256)])
    address = StringField('Address', [validators.Length(min=1, max=256)])
    phone = StringField('Phone Number', [validators.Length(min=2, max=15)])
    # med_doc = FileField('Medical document',
    #                     validators=[
    #                         FileRequired(),
    #                         FileAllowed(ALLOWED_EXTENSIONS, 'Only images like jpg png')])
    sport_rank = StringField('Sport Rank', [validators.Length(min=1, max=256)])
    birthday = DateField('Birthday', [validators.DataRequired(min(time.localtime()))])


class EditEmpForm(Form):
    email = StringField('Email', [validators.Length(min=1, max=254)])
    role_name = RadioField(
        'Роль',
        [validators.DataRequired()],
        choices=[
                ('Admin', 'Адміністратор'),
                ('Coach', 'Тренер'),
                ('Client', 'Клієнт'),
                ('Guest', 'Гість'),
                ]
    )
    first_name = StringField('First Name', [validators.Length(min=1, max=256)])
    second_name = StringField('Second Name', [validators.Length(min=1, max=256)])
    last_name = StringField('Last Name', [validators.Length(min=1, max=256)])
    address = StringField('Address', [validators.Length(min=1, max=256)])
    phone = StringField('Phone Number', [validators.Length(min=2, max=15)])
    # med_doc = FileField('Medical document',
    #                     validators=[
    #                         FileRequired(),
    #                         FileAllowed(ALLOWED_EXTENSIONS, 'Only images like jpg png')])
    sport_rank = StringField('Sport Rank', [validators.Length(min=1, max=256)])
    birthday = DateField('Birthday', [validators.DataRequired(min(time.localtime()))])


class SearchStuffForm(Form):
    email = StringField('Email', [validators.Length(max=254)])
    # role_name = SelectMultipleField('Role Name',
    #                                  [validators.DataRequired()],
    #                                  choices=[
    #                                      ('Admin', 'Адміністратор'),
    #                                      ('Coach', 'Тренер'),
    #                                      ('Client', 'Клієнт'),
    #                                      ('Guest', 'Гість'),
    #                                  ], default='Admin'
    #                                  )
    string_of_files = ['Admin\r\nCoach\r\nClient\r\nGuest\r\n']
    list_of_files = string_of_files[0].split()
    # create a list of value/description tuples
    files = [(x, x) for x in list_of_files]
    role_name = MultiCheckboxField('Роль', choices=[
                ('Admin', 'Адміністратор'),
                ('Coach', 'Тренер'),
                ('Client', 'Клієнт'),
                ('Guest', 'Гість'),
                ])
    first_name = StringField('First Name', [validators.Length(max=256)])
    second_name = StringField('Second Name', [validators.Length(max=256)])
    last_name = StringField('Last Name', [validators.Length(max=256)])
    sport_rank = StringField('Sport Rank', [validators.Length(max=256)])
    filter_switcher = RadioField(
        'Order by',
        [validators.DataRequired()],
        choices=[
                ('email', 'Email'),
                ('role_name', 'Role Name'),
                ('first_name', 'First Name'),
                ('second_name', 'Second Name'),
                ('last_name', 'Last Name'),
                ('sport_rank', 'Sport rank'),
                ], default='email'
    )


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        email = form.email.data
        password = sha256_crypt.encrypt(str(form.password.data))
        confirm_password = form.confirm_password.data
        first_name = form.first_name.data
        second_name = form.second_name.data
        last_name = form.last_name.data
        address = form.address.data
        phone = form.phone.data
        # med_doc = form.med_doc.data
        # filename = secure_filename(med_doc.filename)
        # med_doc.save(os.path.join(
        #     UPLOAD_FOLDER, '/', filename
        # ))

        # Do something with it!!
        sport_rank = form.sport_rank.data
        birthday = form.birthday.data
        uc.__enter__()
        uc.add_user(email, password, first_name, second_name, last_name, address, phone, UPLOAD_FOLDER + '/empty', sport_rank, birthday)
        uc.__exit__()
        flash('You are now registered and can log in', 'success')
        return render_template('registration.html', form=form)
    return render_template('registration.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_name = request.form['username']
        password_candidate = request.form['password']
        uc.__enter__()
        if not uc.get_user_login_data(user_name, password_candidate):
            error = 'Username or password is wrong'
            uc.__exit__()
            return render_template('login.html', error=error)
        else:
            flash('You are log in', 'success')
            session['logged_in'] = True
            session['username'] = user_name
            uc.__exit__()
            return redirect(url_for('profile'))

    return render_template('login.html')


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap


@app.route('/profile')
@is_logged_in
def profile():
    if 'logged_in' in session:
        uc.__enter__()
        user_role = uc.get_user_role(session['username'])
        u_fsl = uc.get_user_fsl_name(session['username'], user_role)
        session['user_role'] = user_role
        uc.__exit__()
        if user_role == 'None':
            return redirect('logout')
        # flash(u_fsl)
        return render_template('profile.html', user_role=user_role, f_name=u_fsl[0], s_name=u_fsl[1], l_name=u_fsl[2])
    else:
        return redirect(url_for('index'))


@app.route('/manage_user', methods=['GET', 'POST'])
@is_logged_in
def manage_user():
    form = SearchStuffForm(request.form)
    if 'logged_in' in session and request.method == 'GET':
        if session['user_role'] == 'Admin':
            uc.__enter__()
            _user_role = uc.get_user_role(session['username'])
            session['user_role'] = _user_role
            if _user_role != 'Admin':
                uc.__exit__()
                return redirect(url_for('index'))
            else:
                uc.__exit__()
                return render_template('manage_user.html', form=form)
        else:
            return redirect(url_for('index'))
    elif 'logged_in' in session and request.method == 'POST' and form.validate():
        if session['user_role'] == 'Admin':
            uc.__enter__()
            user_role = uc.get_user_role(session['username'])
            session['user_role'] = user_role
            email = form.email.data
            role_name = form.role_name.data
            first_name = form.first_name.data
            second_name = form.second_name.data
            last_name = form.last_name.data
            sport_rank = form.sport_rank.data
            order = form.filter_switcher.data
            app.logger.info('INPUT DATA IS')
            app.logger.info(', '.join([email, '['+', '.join(role_name)+']', first_name, second_name, last_name, sport_rank, order]))
            stuff_list = uc.get_user_data(email, role_name, first_name, second_name, last_name, sport_rank, order)
            uc.__exit__()
            app.logger.info('STUFF LIST IS')
            app.logger.info(stuff_list)
            return render_template('manage_user.html', form=form, stuff=stuff_list, localization=ROLE_IN_UKR)
        else:
            return redirect(url_for('index'))

    elif 'logged_in' in session and request.method == 'POST' and not form.validate():
        if session['user_role'] == 'Admin':
            uc.__enter__()
            user_role = uc.get_user_role(session['username'])
            session['user_role'] = user_role
            uc.__exit__()
            return render_template('manage_user.html', form=form)
        else:
            return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))


@app.route('/manage_team', methods=['GET', 'POST'])
@is_logged_in
def manage_team():
    form = SearchStuffForm(request.form)
    if 'logged_in' in session and request.method == 'GET':
        if session['user_role'] == 'Admin':
            uc.__enter__()
            _user_role = uc.get_user_role(session['username'])
            session['user_role'] = _user_role
            if _user_role != 'Admin':
                uc.__exit__()
                return redirect(url_for('index'))
            else:
                uc.__exit__()
                return render_template('manage_team.html', form=form)
        else:
            return redirect(url_for('index'))
    elif 'logged_in' in session and request.method == 'POST' and form.validate():
        if session['user_role'] == 'Admin':
            uc.__enter__()
            user_role = uc.get_user_role(session['username'])
            session['user_role'] = user_role
            email = form.email.data
            role_name = form.role_name.data
            first_name = form.first_name.data
            second_name = form.second_name.data
            last_name = form.last_name.data
            sport_rank = form.sport_rank.data
            order = form.filter_switcher.data
            app.logger.info('INPUT DATA IS')
            app.logger.info(', '.join([email, '['+', '.join(role_name)+']', first_name, second_name, last_name, sport_rank, order]))
            stuff_list = uc.get_user_data(email, role_name, first_name, second_name, last_name, sport_rank, order)
            uc.__exit__()
            app.logger.info('STUFF LIST IS')
            app.logger.info(stuff_list)
            return render_template('manage_team.html', form=form, stuff=stuff_list, localization=ROLE_IN_UKR)
        else:
            return redirect(url_for('index'))

    elif 'logged_in' in session and request.method == 'POST' and not form.validate():
        if session['user_role'] == 'Admin':
            uc.__enter__()
            user_role = uc.get_user_role(session['username'])
            session['user_role'] = user_role
            uc.__exit__()
            return render_template('manage_team.html', form=form)
        else:
            return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))


@app.route('/edit_user?<string:user_email>;<string:user_role>', methods=['GET', 'POST'])
@is_logged_in
def edit_user(user_email, user_role):
    form = EditEmpForm(request.form)
    if 'logged_in' in session and request.method == 'GET':
        if session['user_role'] == 'Admin':
            uc.__enter__()
            _user_role = uc.get_user_role(session['username'])
            session['user_role'] = _user_role
            if _user_role != 'Admin':
                uc.__exit__()
                return redirect(url_for('index'))
            # uc.__exit__()
            # # user_email = request.args['_email']
            # uc.__enter__()
            user_data = []
            if user_role is not None:
                if user_role == 'Admin' or user_role == 'Coach':
                    user_data = uc.get_emp(user_email)
                elif user_role == 'Client':
                    user_data = uc.get_client(user_email)
                elif user_role == 'Guest':
                    user_data = uc.get_guest(user_email)
            app.logger.info(user_email)
            app.logger.info(user_data)
            uc.__exit__()
            if user_data is None:
                return redirect(url_for('manage_user'))
            form.email.data = user_data[0]
            form.role_name.data = user_data[1]
            form.first_name.data = user_data[2]
            form.second_name.data = user_data[3]
            form.last_name.data = user_data[4]
            form.address.data = user_data[5]
            form.phone.data = user_data[6]
            form.sport_rank.data = user_data[7]
            form.birthday.data = user_data[8]
            return render_template('edit_user.html', form=form)
        else:
            return redirect(url_for('index'))

    elif 'logged_in' in session and request.method == 'POST' and form.validate():
        if session['user_role'] == 'Admin':
            email = request.form['email']
            role_name = request.form['role_name']
            first_name = request.form['first_name']
            second_name = request.form['second_name']
            last_name = request.form['last_name']
            address = request.form['address']
            phone = request.form['phone']
            sport_rank = request.form['sport_rank']
            birthday = request.form['birthday']
            uc.__enter__()
            # flash(birthday)
            # uc.update_user(email, role_name, first_name, second_name, last_name, address, phone, UPLOAD_FOLDER + '/empty',
            #                sport_rank, birthday)
            uc.update_user(email=email, role_name=role_name, first_name=first_name, second_name=second_name, last_name=last_name,
                           address=address, phone=phone, med_doc=UPLOAD_FOLDER + '/empty', sport_rank=sport_rank,
                           birthday=birthday)
            uc.__exit__()
            form.email.data = email
            form.role_name.data = role_name
            form.first_name.data = first_name
            form.second_name.data = second_name
            form.last_name.data = last_name
            form.address.data = address
            form.phone.data = phone
            form.sport_rank.data = sport_rank
            form.birthday.data = birthday
            flash('User is updated', 'success')
            return render_template('edit_user.html', form=form)
    return render_template('edit_user.html', form=form)


@app.route('/logout')
def logout():
    session.clear()
    flash("You are now logged out", "success")
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
