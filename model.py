from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
import hashlib
import string
import random
import datetime


db = SQLAlchemy()  

def pwhash(pw, salt):
    return hashlib.sha512(pw.encode('ASCII') + salt.encode('ASCII')).hexdigest()

def salt(length):
    s = []
    for _ in range(length):
        s.append(random.choice(string.ascii_letters))
    return ''.join(s)

class User(db.Model):
    __tablename__= 'users'
    
    DRIVER = 'driver'
    ADMIN = 'admin'
    
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    username = db.Column('username', db.String(80), nullable=False, unique=True)
    password = db.Column('password', db.String(30), nullable=False)
    first_name = db.Column('first_name', db.String(100), nullable=False)
    last_name = db.Column('last_name', db.String(100), nullable=False)
    email = db.Column('email', db.String(120), nullable=False)
    phone = db.Column('phone', db.String(20), nullable=True)
    acct_type = db.Column('acct_type', db.Enum(DRIVER, ADMIN, name='account_type_enum'), nullable=False)
    active = db.Column('active', db.Boolean, default=True, nullable=False)
        
    def check_pw(self, pw):
        return pw.strip() == self.password.strip()
   
    def __init__(self, un, pw, first, last, acct_type, email=None, phone=None):
        self.username = un.strip()
        self.password = pw.strip()
        self.first_name = first
        self.last_name = last
        self.acct_type = acct_type
        self.email = email
        self.phone = phone
    @staticmethod
    def username_exits(un):
        return User.query.filter_by(username=un).count() > 0
    

class Agency(db.Model):
    __tablename__ = 'agencies'
    
    DONOR = 'donor'
    RECIPIENT = 'recipient'
    
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    name = db.Column('name', db.String(200), nullable=False, unique=True)
    agency_type = db.Column('type', db.Enum(DONOR, RECIPIENT, name='agency_type_enum'), nullable=False)
    address = db.Column('address', db.String(200))
    city = db.Column('city', db.String(50))
    state = db.Column('state', db.String(4))
    zip = db.Column('zip', db.String(7))
    contact = db.Column('contact', db.String(200))
    phone = db.Column('phone', db.String(200))
    notes = db.Column('notes', db.String(500))
    active = db.Column('active', db.Boolean, default=True, nullable=False)
    
    
class DriverSchedule(db.Model):
    __tablename__ = 'driver_schedule'
    
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    driver_id = db.Column('driver', db.ForeignKey(User.id), nullable=True, default=None, unique=True)
    name = db.Column('name', db.String(200), nullable=False, unique=True)
    
    driver = relationship('User', backref='schedule')
    items = relationship('DriverScheduleItem', backref='schedule')
    
class DriverScheduleItem(db.Model):
    __tablename__ = 'driver_schedule_item'
    
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    schedule_id = db.Column('schedule', db.ForeignKey(DriverSchedule.id), nullable=False)
    agency_id = db.Column('agency', db.ForeignKey(Agency.id), nullable=False)
    day_of_week = db.Column('day_of_week', db.Integer, nullable=False)
    position_in_day = db.Column('position_in_day', db.Integer, nullable=False)
    skip_next = db.Column('skip_next', db.Boolean, nullable=False, default=False)
    
    agency = relationship('Agency')

class DriverDailyRoute(db.Model):
    __tablename__ = 'driver_daily_route'
    
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    driver_id = db.Column('driver', db.ForeignKey(User.id), nullable=False)
    date = db.Column('date', db.Date())
    
    driver = relationship('User')
    stops = relationship('DriverStop', backref='route', order_by='DriverStop.position_in_day')
    
    def totals(self):
        totals = \
        {
            'Prepared': [0.0, 0.0],
            'Produce': [0.0, 0.0],
            'Dairy': [0.0, 0.0],
            'Raw Meat': [0.0, 0.0],
            'Perishable': [0.0, 0.0],
            'Dry Goods': [0.0, 0.0],
            'Bread': [0.0, 0.0],
        }
        total = [0.0, 0.0]
        for stop in self.stops:
            i = 0 if stop.agency.agency_type == Agency.DONOR else 1
            totals['Prepared'][i] += stop.prepared
            totals['Produce'][i] += stop.produce
            totals['Dairy'][i] += stop.dairy
            totals['Raw Meat'][i] += stop.raw_meat
            totals['Dry Goods'][i] += stop.dry_goods
            totals['Bread'][i] += stop.bread
            totals['Perishable'][i] += stop.perishable
            
        for thing in totals:
            total[0] += totals[thing][0]
            total[1] += totals[thing][1]
        return (total, totals)

class DriverStop(db.Model):
    __tablename__ = 'driver_stops'
    
    id = db.Column('id', db.Integer, primary_key=True, autoincrement=True)
    schedule_id = db.Column('driver_daily_route', db.ForeignKey(DriverDailyRoute.id), nullable=False)
    agency_id = db.Column('agency', db.ForeignKey(Agency.id), nullable=False, index=True)
    position_in_day = db.Column('position_in_day', db.Integer, nullable=False)
    time = db.Column('time', db.Time())
    agency = relationship('Agency')
    special_stop = db.Column('special_stop', db.Boolean(), default=False, nullable=False)
    notes = db.Column('notes', db.String(500))
    
    cargo_temp = db.Column('cargo_temp', db.Integer(), default=0)
    prepared = db.Column('prepared', db.Integer(), default=0)
    produce = db.Column('produce', db.Integer(), default=0)
    dairy = db.Column('dairy', db.Integer(), default=0)
    raw_meat = db.Column('raw_meat', db.Integer(), default=0)
    perishable = db.Column('perishable', db.Integer(), default=0)
    dry_goods = db.Column('dry_goods', db.Integer(), default=0)
    bread = db.Column('bread', db.Integer(), default=0)
    
    def total_up(self):
        return self.prepared + self.produce + self.dairy + \
                self.raw_meat + self.perishable + self.dry_goods + \
                self.bread
    
def reset_db():
    print('Dropping Old DB')
    db.drop_all()
    print('Creating new DB')
    db.create_all()
    print('Adding default admin')
    u = User('admin', 'password', 'Table_to_Table', 'Admin', User.ADMIN, 'admin@t2t.com', None)
    db.session.add(u)
    db.session.commit()
    print('Finished!')
    
def fill_with_test():
    db.drop_all()
    db.create_all()
    u = User('admin', 'password', 'Table_to_Table', 'Admin', User.ADMIN, 'admin@t2t.com', None)
    db.session.add(u)
    db.session.commit()
    
    drivers = []
    ages = []
    
    for i in range(15):
        u = User('driver' + str(i), 'password', 'FirstName' + str(i), 'LastName' + str(i), User.DRIVER, 'driver' + str(i) + '@t2t.com', '123456789')
        drivers.append(u)
        db.session.add(u)
    db.session.commit()
    
    cities = ('Ridgewood', 'Fair Lawn', 'Newark', 'Paramus', 'Paterson', 'Mahwah', 'Midland Park')
    words = ['and', 'for', 'drop', 'off', 'food', 'stuff', 'back', 'front', 'door']
    def rand_sentense():
        s = ''
        for _ in range(random.randint(0, 8)):
            s += random.choice(words) + ' '
        return s.strip()
    
    for i in range(100):
        d = Agency()
        d.address = str(random.randint(1, 999) + 1) + ' Donor' + str(i) + ' Ave'
        d.city = random.choice(cities)
        d.agency_type = Agency.DONOR
        d.name = 'Donor' + str(i)
        d.contact = 'Donor Person' + str(i)
        d.phone = str(random.randint(1, 1000000000))
        d.notes = rand_sentense()
        ages.append(d)
        
        r = Agency()
        r.address = str(random.randint(1, 999) + 1) + ' Recipient' + str(i) + ' Ave'
        r.city = random.choice(cities)
        r.agency_type = Agency.RECIPIENT
        r.name = 'Recipient' + str(i)
        r.contact = 'Recipient Person' + str(i)
        r.phone = str(random.randint(100000, 1000000000))
        r.notes = rand_sentense()
        ages.append(r)
        
        db.session.add(r)
        db.session.add(d)
    
    today = datetime.datetime.today()
    cur = today - datetime.timedelta(days=365 * 1)
    db.session.commit()
    
    while cur <= today:
        print(cur)
        for d in drivers:
            if not random.randint(0, 25):
                continue
            r = DriverDailyRoute()
            r.driver_id = d.id
            r.date = cur
            db.session.add(r)
            
            t = datetime.datetime(2019, 11, 25, hour=6)
            
            for i in range(random.randint(20, 40)):
                s = DriverStop()
                
                s.produce = random.randint(0, 100)
                s.dairy = random.randint(0, 100)
                s.raw_meat = random.randint(0, 100)
                s.bread = random.randint(0, 100)
                s.dry_goods = random.randint(0, 100)
                s.perishable = random.randint(0, 100)
                s.prepared = random.randint(0, 100)
                s.cargo_temp = random.randint(0, 100)
                
                s.agency_id = random.choice(ages).id
                s.position_in_day = i
                
                t += datetime.timedelta(minutes=random.randint(5, 30))
                s.time = t.time()
                
                s.special_stop = not bool(random.randint(0, 20))
                s.notes = rand_sentense()
                
                r.stops.append(s)
                
        db.session.commit()
        cur += datetime.timedelta(days=1)

