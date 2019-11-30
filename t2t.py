from flask import Flask, request, session, url_for, redirect
from flask.templating import render_template
import model
import forms
from functools import wraps
from flask.helpers import flash
from sqlalchemy.sql.functions import func, sum
import re
from jinja2 import Markup, evalcontextfilter, escape
from sqlalchemy.orm import load_only
from sqlalchemy import extract
import datetime
import traceback
import random
import sys
from flask.wrappers import Response
import subprocess
import locale

app = Flask(__name__)
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///t2t.db?check_same_thread=False'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:password@localhost/t2t'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/t2t'
DB_PASSWORD = 'sNT0A=idLbgk2'
DB_NAME = 't2t_routes'
DB_USER = 't2t_routes'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://%s:%s@localhost/%s' % (DB_USER, DB_PASSWORD, DB_NAME)
app.secret_key = '9003626490'

model.db.init_app(app)
model.db.app = app
model.db.create_all()

model.fill_with_test()

locale.setlocale(locale.LC_ALL, '')

def log_except():
    sys.stderr.write(traceback.format_exc() + '\n')
    
def log_message(msg):
    sys.stderr.write(str(msg) + '\n')

@app.template_filter()
@evalcontextfilter
def linebreaks(eval_ctx, value):
    result = str(escape(value))
    result = result.replace('\r\n', '<br/>')
    result = result.replace('\n', '<br/>')
    result = result.replace('\r', '<br/>')
    result = Markup(result)
    return result

@app.template_filter()
def greyzero(value):
    if value == 0:
        value = '<font color="grey">%s</font>' % str(value)
    return Markup(str(value))

@app.template_filter()
def commas(value):
    #return '{0:,d}'.format(int(value))
    return locale.format("%d", value, grouping=True)


def admin_filter(page):
    @wraps(page)
    def _page(**args):
        if not 'user_type' in session or session['user_type'] != model.User.ADMIN:
            return redirect(url_for('login'))
        return page(**args)
    return _page

def driver_filter(page):
    @wraps(page)
    def _page(**args):
        if not 'user_type' in session or session['user_type'] != model.User.DRIVER:
            return redirect(url_for('login'))
        return page(**args)
    return _page

@app.errorhandler(500)
def internal_error(error):
    return "500 error"

def login_filter(page):
    @wraps(page)
    def _page(**args):
        if not 'user_type' in session:
            return redirect(url_for('login'))
        return page(**args)
    return _page         

@app.route('/')
def index():
    if not 'user_type' in session:
        return redirect(url_for('login'))
    elif session['user_type'] == model.User.ADMIN:
        return render_template('admin/admin_base.html', page_title='Admin Home')
    elif session['user_type'] == model.User.DRIVER:
        return redirect(url_for('driver_route_today'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    e = None
    f = forms.LoginForm(request.form)
    if request.method == 'POST' and f.validate():
        u = model.User.query.filter_by(username=f.username.data).all()
        if not u:
            e = 'Username not found.'
        elif not u[0].active:
            e = 'Account has been disabled.'
        elif not u[0].check_pw(f.password.data):
            e = 'Wrong password.'
        else:
            session.clear()
            session['user_id'] = u[0].id
            session['user_type'] = u[0].acct_type
            return redirect(url_for('index'))
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('login.html', form=f, error=e, page_title='Login')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/changepassword', methods=['GET', 'POST'])
@login_filter
def change_password():
    f = forms.ChangePassword(request.form)
    if request.method == 'POST' and f.validate():
        u = model.User.query.get(session['user_id'])
        if u.check_pw(f.old_password.data.strip()):
            u.password = f.new_password.data.strip()
            model.db.session.commit()
            flash('Password Changed')
            return redirect(url_for('index'))
        else:
            model.db.session.rollback()
            f.old_password.errors.append('Wrong current password!')
    return render_template('change_password.html', form=f, page_title='Change Password')

@app.route('/updateaccount', methods=['GET', 'POST'])
@login_filter
def update_account():
    f = forms.AccountUpdate(request.form)
    u = model.User.query.get(session['user_id'])
    if request.method == 'POST':
        if f.validate():
            try:
                f.load_account(u)
                model.db.session.commit()
                return redirect(url_for('index'))
            except:
                model.db.session.rollback()
                flash('Database Error! Can not update account.', 'error')
                log_except()
    else:
        f.load_from_account(u)
    return render_template('update_account.html', form=f, page_title='Update Account')

@app.route('/admin/drivers/', methods=['GET', 'POST'])
@admin_filter
def admin_drivers():
    if request.method == 'POST' and 'did' in request.form and 'sid' in request.form:
        try:
            did = int(request.form['did'])
            d = model.User.query.get(did)
            assert d and d.acct_type == model.User.DRIVER
            for s in model.DriverSchedule.query.filter_by(driver_id = did).all():
                s.driver_id = None
            sid = request.form['sid']
            if sid and sid != 'None':
                model.DriverSchedule.query.get(int(sid)).driver_id = did
            model.db.session.commit()
            flash('Schedule Updated')
            return redirect(request.url)
        except:
            model.db.session.rollback()
            flash('Database Error! Can not update schedule.', 'error')
            log_except()
    elif request.method == 'POST' and 'reactivate' in request.form:
        try:
            did = int(request.form['reactivate'])
            d = model.User.query.get(did)
            assert d.acct_type == model.User.DRIVER
            d.active = True
            model.db.session.commit()
            return redirect(request.url)
        except:
            model.db.session.rollback()
            flash('Database Error! Can not reactivate driver.', 'error')
            log_except()
    elif request.method == 'POST' and 'deactivate' in request.form:
        try:
            did = int(request.form['deactivate'])
            d = model.User.query.get(did)
            assert d.acct_type == model.User.DRIVER
            d.active = False
            d.schedule.clear()
            model.db.session.commit()
            return redirect(request.url)
        except:
            model.db.session.rollback()
            flash('Database Error! Can not deactivate driver.', 'error')
            log_except()
    elif request.method == 'POST' and 'resetpw' in request.form:
        try:
            did = int(request.form['resetpw'])
            d = model.User.query.get(did)
            assert d.acct_type == model.User.DRIVER
            newpw = ''.join([str(random.randrange(10)) for _ in range(10)])
            d.password = newpw
            model.db.session.commit()
            flash('Password for ' + d.username + ' reset to ' + newpw + '\nPlease notify the driver of their new password so they can change it.')
            return redirect(request.url)
        except:
            model.db.session.rollback()
            flash('Database Error! Can not reset password!', 'error')
            log_except()
            
    drivers = model.User.query.filter_by(acct_type = model.User.DRIVER).order_by(func.lower(model.User.last_name), 
                                                                                 func.lower(model.User.first_name),
                                                                                 func.lower(model.User.username)).all()
    return render_template('admin/drivers.html', drivers=drivers, page_title='Driver Accounts', schedules=model.DriverSchedule.query.all())

@app.route('/admin/drivers/new', methods=['GET', 'POST'])
@admin_filter
def admin_drivers_new():
    f = forms.NewDriver(request.form)
    if request.method == 'POST' and f.validate():
        try:
            d = f.make_driver()
            model.db.session.add(d)
            model.db.session.commit()
            flash('Driver Added')
            return redirect(url_for('admin_drivers'))
        except:
            model.db.session.rollback()
            flash('Database Error! Can not create new driver.', 'error')
            log_except()
    return render_template('admin/new_driver.html', form=f, page_title='New Driver')

@app.route('/admin/drivers/edit/<int:did>', methods=['GET', 'POST'])
@login_filter
def admin_drivers_edit(did):
    f = forms.AccountUpdate(request.form)
    u = model.User.query.get(did)
    assert u and u.acct_type == model.User.DRIVER
    if request.method == 'POST':
        if f.validate():
            try:
                f.load_account(u)
                model.db.session.commit()
                flash('Driver account updated.')
                return redirect(url_for('admin_drivers'))
            except:
                model.db.session.rollback()
                flash('Database Error! Can not update account.', 'error')
                log_except()
    else:
        f.load_from_account(u)
    return render_template('update_account.html', form=f, page_title='Update Account (' + u.username + ')')

@app.route('/admin/agencies/')
@admin_filter
def admin_agencies():
    if 'reactivate' in request.args:
        try:
            aid = int(request.args['reactivate'])
            a = model.Agency.query.get(aid)
            a.active = True
            model.db.session.commit()
        except:
            model.db.session.rollback()
            flash('Database Error! Can not reactivate agency.', 'error')
            log_except()
    elif 'deactivate' in request.args:
        try:
            aid = int(request.args['deactivate'])
            a = model.Agency.query.get(aid)
            assert a
            a.active = False
            model.DriverScheduleItem.query.filter_by(agency_id=aid).delete()
            model.db.session.commit()
        except:
            model.db.session.rollback()
            flash('Database Error! Can not deactivate agency.', 'error')
            log_except()
    agencies = model.Agency.query.order_by(func.lower(model.Agency.name)).all()
    return render_template('admin/agencies.html', agencies=agencies, page_title='Agencies')

@app.route('/admin/agencies/new', methods=['GET', 'POST'])
@admin_filter
def admin_agencies_new():
    f = forms.AgencyForm(request.form)
    if request.method == 'POST' and f.validate():
        try:
            a = f.make_agency()
            model.db.session.add(a)
            model.db.session.commit()
            flash('Agency Added')
            return redirect(url_for('admin_agencies'))
        except:
            model.db.session.rollback()
            flash('Database Error! Can not create new agency.', 'error')
            log_except()
    return render_template('admin/edit_agency.html', form=f, page_title='New Agency')

@app.route('/admin/agencies/edit/<int:aid>', methods=['GET', 'POST'])
@admin_filter
def admin_agencies_edit(aid):
    f = forms.AgencyForm(request.form)
    if request.method == 'POST' and f.validate():
        try:
            a = model.Agency.query.get(aid)
            f.load_agency(a)
            model.db.session.commit()
            flash('Agency Changed')
            return redirect(url_for('admin_agencies'))
        except:
            model.db.session.rollback()
            flash('Database Error! Can not update agency.', 'error')
            log_except()
    elif request.method == 'GET':
        f.load_from_agency(model.Agency.query.get(aid))
        
    return render_template('admin/edit_agency.html', form=f, page_title='Edit Agency')

@app.route('/admin/schedules', methods=['GET', 'POST'])
@admin_filter
def admin_schedules():
    f = forms.CreateSchedule(request.form)
    if request.method == 'POST' and f.validate():
        try:
            s = model.DriverSchedule()
            s.driver_id = None
            s.name = f.name.data.strip()
            model.db.session.add(s)
            model.db.session.commit()
            flash('New Schedule')
            return redirect(url_for('admin_schedule_edit', sid=s.id))
        except:
            model.db.session.rollback()
            flash('Database Error! Can not create new schedule.', 'error')
            log_except()
            
    if 'del' in request.args and request.args['del']:
        try:
            model.DriverScheduleItem.query.filter_by(schedule_id=int(request.args['del'])).delete()
            model.DriverSchedule.query.filter_by(id=int(request.args['del'])).delete()
            model.db.session.commit()
            flash('Deleted')
        except:
            model.db.session.rollback()
            flash('Database Error! Can not delete schedule.', 'error')
            log_except()
        
    return render_template('admin/schedules.html', page_title='Schedules', form=f, schedules=model.DriverSchedule.query.all())

@app.route('/admin/editschedule/<int:sid>', methods=['GET', 'POST'])
@admin_filter
def admin_schedule_edit(sid):
    s = model.DriverSchedule.query.get(sid)
    assert s
    f = forms.CreateSchedule(request.form)
    if not f.name.data:
        f.name.data = s.name
    
    if request.method == 'POST':
        try:
            if f.name.data != s.name and f.validate():
                s.name = f.name.data.strip()
                
            model.DriverScheduleItem.query.filter_by(schedule_id=sid).delete()
            for field in request.form:
                if not field.startswith('item_'):
                    continue
                v = request.form[field]
                if not v or not v.isdigit():
                    continue
                field = field.split('_')
                day = int(field[1])
                pos = int(field[2])
                assert day >= 0 and day < 7 and pos >= 0 and pos <= 50
                a_id = int(v);
                itm = model.DriverScheduleItem()
                itm.day_of_week = day
                itm.position_in_day = pos
                itm.agency_id = a_id
                itm.skip_next = 'skip_' + str(day) + '_' + str(pos) in request.form
                s.items.append(itm)
               
            model.db.session.commit()
            flash('Schedule Saved!')
        except:
            model.db.session.rollback()
            flash('Error updating schedule!', 'error')
            log_except()
                    
    ages = model.Agency.query.options(load_only('id', 'name')).filter_by(active=True).order_by(func.lower(model.Agency.name)).all()
    ages = [(a.id, a.name) for a in ages]
    schedule = s.items
    rows = 50
    for itm in schedule:
        if itm.position_in_day + 1 > rows:
            rows = itm.position_in_day
    schedule_list = [([None] * rows) for day in range(7)]
    for itm in schedule:
        schedule_list[itm.day_of_week][itm.position_in_day] = (itm.agency_id, itm.skip_next)
        
    return render_template('admin/edit_schedule.html', select_values=schedule_list, agencies=ages, 
                            rows=rows, page_title='Edit Schedule - ' + s.name, form=f)
@app.route('/admin/printschedules')
@admin_filter
def admin_print_schedules():
    schedules = []
    for week in model.DriverSchedule.query.all():
        days = [[] for _ in range(7)]
        for item in week.items:
            days[item.day_of_week].append(item)
        for day in days:
            day.sort(key=lambda d: d.position_in_day)
        schedules.append((week, days))   
    return render_template('admin/print_schedules.html', schedules=schedules)

def sum_results(z):
    s = 0
    for x in z:
        if x: s += x
    return s   
 
@app.route('/admin/lbspercity')
@admin_filter
def admin_lbs_per_city():
    year = datetime.datetime.today().year
    if 'year' in request.args:
        try:
            year = int(request.args['year'])
        except:
            flash('Could not parse year.', 'error')
    cities = {}
    
    q = model.db.session.query(model.Agency.city, model.Agency.agency_type, extract('month', model.DriverDailyRoute.date),
                               sum(model.DriverStop.prepared), sum(model.DriverStop.produce),
                               sum(model.DriverStop.dairy), sum(model.DriverStop.raw_meat),
                               sum(model.DriverStop.perishable), sum(model.DriverStop.dry_goods),
                               sum(model.DriverStop.bread)).\
                join(model.DriverStop, model.DriverDailyRoute).\
                filter(extract('year', model.DriverDailyRoute.date) == year).\
                group_by(model.Agency.city, model.Agency.agency_type, extract('month', model.DriverDailyRoute.date))
    for r in q:
        city = r[0]
        atype = r[1]
        month = int(r[2])
        r = r[3:]
        
        if not city in cities:
            cities[city] = [[0, 0] for _ in range(12)]
        if atype == model.Agency.DONOR:
            cities[city][month - 1][0] = sum_results(r)
        else:
            cities[city][month - 1][1] = sum_results(r)
        
    cities = [(k, cities[k]) for k in sorted(cities)]
    
    return render_template('admin/lbs_per_city.html', year=year, cities=cities, page_title='Pounds Per City (' + str(year) + ')')

@app.route('/admin/lbsperagency')
@admin_filter
def admin_lbs_per_agency():
    year = datetime.datetime.today().year
    if 'year' in request.args:
        try:
            year = int(request.args['year'])
        except:
            flash('Could not parse year.', 'error')
    agencies = {model.Agency.DONOR: {}, model.Agency.RECIPIENT: {}}
    
    q = model.db.session.query(model.Agency.name, model.Agency.agency_type, extract('month', model.DriverDailyRoute.date), 
                               sum(model.DriverStop.prepared), sum(model.DriverStop.produce),
                               sum(model.DriverStop.dairy), sum(model.DriverStop.raw_meat),
                               sum(model.DriverStop.perishable), sum(model.DriverStop.dry_goods),
                               sum(model.DriverStop.bread)).\
                join(model.DriverStop, model.DriverDailyRoute).\
                filter(extract('year', model.DriverDailyRoute.date) == year).\
                group_by(model.Agency.name, extract('month', model.DriverDailyRoute.date))
    for r in q:
        agency = r[0]
        if 'aggregate' in request.args:
            agency = agency.split(',')[0]
            
        type = r[1]
        month = int(r[2])
        if not agency in agencies[type]:
            agencies[type][agency] = \
            {
                'Prepared': [0] * 12,
                'Produce': [0] * 12,
                'Dairy': [0] * 12,
                'Raw Meat': [0] * 12,
                'Perishable': [0] * 12,
                'Dry Goods': [0] * 12,
                'Bread': [0] * 12,
                'TOTAL': [0] * 12,
            }
        r = r[3:]
        
        agencies[type][agency]['Prepared'][month - 1] += r[0] if r[0] else 0
        agencies[type][agency]['Produce'][month - 1] += r[1] if r[1] else 0
        agencies[type][agency]['Dairy'][month - 1] += r[2] if r[2] else 0
        agencies[type][agency]['Raw Meat'][month - 1] += r[3] if r[3] else 0
        agencies[type][agency]['Perishable'][month - 1] += r[4] if r[4] else 0
        agencies[type][agency]['Dry Goods'][month - 1] += r[5] if r[5] else 0
        agencies[type][agency]['Bread'][month - 1] += r[6] if r[6] else 0
        agencies[type][agency]['TOTAL'][month - 1] += sum_results(r)
    
    #remove loop if category support is required for recipients
    for agency in agencies[model.Agency.RECIPIENT]:
        dlist = []
        for cat in agencies[model.Agency.RECIPIENT][agency]:
            if cat != 'TOTAL':
                dlist.append(cat)
        for cat in dlist:
            del agencies[model.Agency.RECIPIENT][agency][cat]
    
    agencies[model.Agency.RECIPIENT] = [(k, agencies[model.Agency.RECIPIENT][k]) for k in sorted(agencies[model.Agency.RECIPIENT])]
    agencies[model.Agency.DONOR] = [(k, agencies[model.Agency.DONOR][k]) for k in sorted(agencies[model.Agency.DONOR])]

    return render_template('admin/lbs_per_agency.html', year=year, agencies=agencies, page_title='Pounds Per Agency (' + str(year) + ')')

@app.route('/admin/driverrecords/<int:did>', methods=['GET', 'POST'])
@admin_filter
def admin_driver_records(did):
    driver = model.User.query.get(did)
    assert driver and driver.acct_type == model.User.DRIVER
    
    records = []
    date = datetime.date.today()
    if 'date' in request.args:
        try:
            date = datetime.datetime.strptime(request.args['date'], '%Y-%m')
        except:
            flash('Bad date format.', 'error')
    
    if request.method == 'POST' and 'add_day' in request.form and request.form['add_day'] != 'None':
        try:
            add_date = datetime.datetime.strptime(request.form['add_day'], '%Y-%m-%d')
            count = model.DriverDailyRoute.query.filter(model.DriverDailyRoute.driver_id == did,
                                                extract('month', model.DriverDailyRoute.date) == add_date.month,
                                                extract('year', model.DriverDailyRoute.date) == add_date.year, 
                                                extract('day', model.DriverDailyRoute.date) == add_date.day).count()
            if not count:                                   
                r = model.DriverDailyRoute()
                r.driver_id = did
                r.date = add_date
                model.db.session.add(r)
                model.db.session.commit()
            else:
                flash('Record already exists.', 'error')
            return redirect(request.url)
        except:
            model.db.session.rollback()
            flash('Error adding record!', 'error')
            log_except()
        
    
    display = None
    if 'display' in request.args:
        display = model.DriverDailyRoute.query.get(int(request.args['display']))
    
    if display and request.method == 'POST' and 'add_stop' in request.form and request.form['add_stop'] != 'None':
        a = model.Agency.query.get(int(request.form['add_stop']))
        assert a
        try:
            s = model.DriverStop()
            s.agency_id = a.id
            s.position_in_day = len(display.stops)
            s.time = None
            display.stops.append(s)
            model.db.session.commit()
            return redirect(request.url)
        except:
            model.db.session.rollback()
            flash('Error adding record!', 'error')
            log_except()
    
    if display and request.method == 'POST' and 'delete_stop' in request.form:
        try:
            r = model.DriverStop.query.get(int(request.form['delete_stop']))
            assert r and r.schedule_id == display.id
            model.db.session.delete(r)
            model.db.session.commit()
            return redirect(request.url)
        except:
            model.db.session.rollback()
            flash('Error removing record!', 'error')
            log_except()
    records = model.DriverDailyRoute.query.filter(model.DriverDailyRoute.driver_id == did, 
                                                  extract('month', model.DriverDailyRoute.date) == date.month,
                                                  extract('year', model.DriverDailyRoute.date) == date.year).order_by(model.DriverDailyRoute.date).all()
    day_used = [False] * 32
    for r in records:
        day_used[r.date.day] = True                                        
    date_counter = datetime.datetime(date.year, date.month, 1)
    unused_dates = []
    while date_counter.month == date.month:
        if not day_used[date_counter.day]:
            unused_dates.append(date_counter)
        date_counter += datetime.timedelta(days=1)
    
    agencies = model.Agency.query.options(load_only(model.Agency.name, model.Agency.id)).all() if display else None
    return render_template('/admin/driver_records.html', records=records, 
                           date=date, display_record=display, agencies=agencies, driver=driver, unused_days=unused_dates, page_title=driver.last_name + ', ' + driver.first_name + ' Records')

    
@app.route('/admin/agencyrecords/<int:aid>')
@admin_filter
def admin_agency_records(aid):
    records = []
    date = datetime.date.today()
    try:
        date = datetime.datetime.strptime(request.args['date'], '%Y-%m')
    except:
        pass
     
    records = model.DriverStop.query.join(model.DriverDailyRoute).filter(model.DriverStop.agency_id == aid,
                                            extract('month', model.DriverDailyRoute.date) == date.month,
                                            extract('year', model.DriverDailyRoute.date) == date.year).order_by(model.DriverDailyRoute.date, model.DriverStop.time).all()
    agency = model.Agency.query.get(aid)
    
    return render_template('/admin/agency_records.html', records=records, 
                           date=date, agency=agency, page_title=agency.name + ' Records')
    
@app.route('/admin/querydb', methods=['GET', 'POST'])
@admin_filter
def admin_query_db():
    if request.method == 'POST':
        query = model.DriverStop.query.join(model.DriverDailyRoute, model.Agency).join(model.User)
        
        if 'date_filter_start' in request.form:
            start = datetime.datetime.strptime(request.form['start_date'], '%Y-%m-%d') -  datetime.timedelta(days=1)
            query = query.filter(model.DriverDailyRoute.date >= start)
        
        if 'date_filter_end' in request.form:
            end = datetime.datetime.strptime(request.form['end_date'], '%Y-%m-%d')
            query = query.filter(model.DriverDailyRoute.date < end)
            
        if not 'recipient' in request.form:
            query = query.filter(model.Agency.agency_type != model.Agency.RECIPIENT)
            
        if not 'donor' in request.form:
            query = query.filter(model.Agency.agency_type != model.Agency.DONOR)
            
        if 'agency_filter' in request.form:
            query = query.filter(model.Agency.id == int(request.form['agency']))
            
        if 'driver_filter' in request.form:
            query = query.filter(model.User.id == int(request.form['driver']))
            
        
        header = ['Username', 'Last Name', 'First Name', 'Agency Name', 
                  'Agency Type', 'City', 'Date', 'Time', 'Is Special Stop', 'Cargo Temperature',
                  'Prepared', 'Produce', 'Dairy', 'Raw Meat', 'Perishable', 'Dry Goods',
                  'Bread', 'Total']
        
        def csv_line(items):
            return ''.join(['"' + str(s).replace('"', '""') + '",' for s in items][:-1])
        def gen_csv():
            yield csv_line(header) + '\n'
            #for q in query.yield_per(100):
            for q in query:
                yield csv_line([q.route.driver.username, q.route.driver.last_name, q.route.driver.first_name,
                         q.agency.name, q.agency.agency_type, q.agency.city, q.route.date, 
                         q.time, q.special_stop, q.cargo_temp, q.prepared, q.produce,
                         q.dairy, q.raw_meat, q.perishable, q.dry_goods, q.bread, q.total_up()]) + '\n'
        
        return Response(gen_csv(), mimetype='text/csv', headers={'Content-Disposition': 'filename="t2t_query.csv"'})
    
    
    drivers = model.User.query.filter_by(acct_type=model.User.DRIVER).order_by(model.User.active, model.User.last_name, model.User.first_name, model.User.username).all()
    agencies = model.Agency.query.order_by(model.Agency.active, model.Agency.name).all()
    
    return render_template('admin/dbquery.html', page_title='Database Query', drivers=drivers, agencies=agencies)

@app.route('/admin/backup')
@admin_filter
def admin_backup():
    cmd = 'mysqldump -u %s -p%s %s | gzip' % (DB_USER, DB_PASSWORD, DB_NAME)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    def stream():
        while True:
            line = p.stdout.readline()
            if not line: break
            yield line
    fn = datetime.datetime.now().strftime("%m-%d-%y_%H_%M_%S_backup.sql.gz")
    return Response(stream(), mimetype='application/x-gzip', headers={'Content-Disposition': 'filename="%s"' % fn})
    
@app.route('/driver/today/make', methods=['POST'])
@driver_filter
def driver_route_maker():
    today = datetime.date.today()
    template = model.DriverScheduleItem.query.join(model.DriverSchedule).filter(model.DriverSchedule.driver_id == session['user_id'],
                                             model.DriverScheduleItem.day_of_week == ((today.weekday() + 1) % 7)).order_by(model.DriverScheduleItem.position_in_day).all()
    
    pos = 0
    try:
        route = model.DriverDailyRoute()
        route.date = today
        route.driver_id = session['user_id']
        model.db.session.add(route)
        
        for template_stop in template:
            if template_stop.skip_next:
                template_stop.skip_next = False
                continue
            stop = model.DriverStop()
            stop.agency_id = template_stop.agency_id
            stop.position_in_day = pos
            stop.date = today
            pos += 1
            stop.time = None
            route.stops.append(stop)
        model.db.session.commit()
    except:
        flash('Database Error')
        model.db.session.rollback()
        log_except()
        
    return redirect(url_for('driver_route_today'))
    

@app.route('/driver/today')
@driver_filter
def driver_route_today():
    today = datetime.date.today()
    route = model.DriverDailyRoute.query.filter(model.DriverDailyRoute.driver_id == session['user_id'],
                                  model.DriverDailyRoute.date == today).first()
    if not route:
        return render_template('driver/driver_load_route.html', page_title='Load Route')
    
    total = route.totals()
    totals = total[1]
    total = total[0]
    
    ages = [('---', '---')] + [(a.id, a.name) for a in model.Agency.query.options(load_only('id', 'name')).order_by(func.lower(model.Agency.name)).all()] 
    special_form = forms.AddSpecialPickup()
    special_form.set_choices(ages)
    return render_template('driver/driver_today.html', page_title='Today\'s Route', route=route, totals=totals, total=total, special_form=special_form)

@app.route('/driver/today/special', methods=['POST'])
@driver_filter
def driver_add_special():
    today = datetime.date.today()
    route = model.DriverDailyRoute.query.filter(model.DriverDailyRoute.driver_id == session['user_id'],
                                  model.DriverDailyRoute.date == today).first()
    if not route:
        return render_template('driver/driver_load_schedule.html', page_title='Load Schedule')
    
    f = forms.AddSpecialPickup(request.form)
    if f.agency.data != '---':
        try:
            stop = model.DriverStop()
            stop.agency_id = f.agency.data
            stop.position_in_day = len(route.stops)
            stop.time = None
            stop.special_stop = True
            route.stops.append(stop)
            model.db.session.commit()
        except:
            flash('Database Error', 'error')
            model.db.session.rollback()
            log_except()
        
    return redirect(url_for('driver_route_today'))

@app.route('/driver/today/removespecial/<int:sid>')
@driver_filter
def driver_remove_special(sid):
    try:
        stop = model.DriverStop.query.get(sid)
        assert stop 
        assert stop.route.driver.id == session['user_id']
        assert stop.special_stop
        model.db.session.delete(stop)
        model.db.session.commit()
    except:
        flash('Database Error', 'error')
        model.db.session.rollback()
        log_except()
    return redirect(url_for('driver_route_today'))
    
@app.route('/driver/stop/<int:sid>', methods=['GET', 'POST'])
@login_filter
def driver_stop(sid):
    f = forms.StopForm(request.form)
    s = model.DriverStop.query.get(sid)
    assert s and (s.route.driver_id == session['user_id'] or session['user_type'] == model.User.ADMIN)
    if request.method == 'POST' and f.validate():
        try:
            f.load_stop(s)
            model.db.session.commit()
            flash('Saved!')
            if session['user_type'] == model.User.DRIVER:
                return redirect(url_for('driver_route_today'))
        except:
            model.db.session.rollback()
            flash('Database Error', 'error')
            log_except()
    else:
        f.load_from_stop(s)
    return render_template('driver/driver_stop.html', form=f, page_title='Stop: ' + s.agency.name, stop=s)

if __name__ == '__main__':
    app.run('0.0.0.0', debug=True, threaded=True)
