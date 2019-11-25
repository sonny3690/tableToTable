from wtforms import Form, TextField, PasswordField, SelectField, TextAreaField, IntegerField
from wtforms.validators import Length, Regexp, EqualTo, Email, ValidationError, NumberRange, DataRequired
import model
import datetime

ALNUM_REGEX = r'^[a-zA-Z0-9_]*$'
ALNUM_SYMB = r'^[a-zA-Z0-9_&@#$!%-.]*$'
NAME_REGEX = r'^[a-zA-Z0-9_&@#$!%-.\s]*$'
UINT_REGEX = r'^[0-9]*$'

class UniqueConstraintFilter:
    def __init__(self, table, col, original_value=None , message='Value not unique.'):
        self.table = table
        self.col = col
        self.original_value = original_value
        self.message = message
    def __call__(self, form, field):
        if field.data and self.original_value and field.data.strip() == self.original_value.strip():
            return
        if self.table.query.filter(self.col == field.data.strip()).count() > 0:
            raise ValidationError(self.message)

class TimeFilter:
    def __call__(self, form, field):
        splt = field.data.split(':')
        
        if len(splt) != 2 or not splt[0].isdigit() or not splt[1].isdigit() \
                or not (0 <= int(splt[0]) < 24) or not (0 <= int(splt[1]) < 60):
            raise ValidationError('Invalid Time Format')
        

class LoginForm(Form):
    username = TextField('Username', [DataRequired(), Regexp(ALNUM_REGEX)])
    password = PasswordField('Password', [DataRequired(), Regexp(ALNUM_SYMB)])

class NewDriver(Form):
    username = TextField('Username', [DataRequired(), UniqueConstraintFilter(model.User, model.User.username),
                                       Regexp(ALNUM_REGEX), Length(min=5, max=80)])
    password = PasswordField('New Password', [DataRequired(), Regexp(ALNUM_SYMB), Length(min=5, max=30)])
    confirm_password = PasswordField('Confirm Password', [DataRequired(), EqualTo('password')])
    first_name = TextField('First Name', [DataRequired(), Regexp(NAME_REGEX), Length(min=1, max=100)])
    last_name = TextField('Last Name', [DataRequired(), Regexp(NAME_REGEX), Length(min=1, max=100)])
    email = TextField('Email Address', [DataRequired(), Email(), Length(max=120)])
    phone = TextField('Phone Number', [Length(max=20), Regexp(r'^[\s0-9()-]*')])
    
    def make_driver(self):
        return model.User(self.username.data.strip(), self.password.data.strip(), 
                          self.first_name.data.strip(), self.last_name.data.strip(), model.User.DRIVER,
                           self.email.data.strip(), self.phone.data.strip())
    
class AccountUpdate(Form):
    username = TextField('Username', [DataRequired(), Regexp(ALNUM_REGEX), Length(min=5, max=80)])
    first_name = TextField('First Name', [DataRequired(), Regexp(NAME_REGEX), Length(min=1, max=100)])
    last_name = TextField('Last Name', [DataRequired(), Regexp(NAME_REGEX), Length(min=1, max=100)])
    email = TextField('Email Address', [DataRequired(), Email(), Length(max=120)])
    phone = TextField('Phone Number', [Length(max=20), Regexp(r'^[\s0-9()-]*')])
    
    def load_from_account(self, u):
        self.username.data = u.username
        self.username.validators.append(UniqueConstraintFilter(model.User, model.User.username, u.username))
        self.first_name.data = u.first_name
        self.last_name.data = u.last_name
        self.email.data = u.email
        self.phone.data = u.phone
    
    def load_account(self, u):
        u.username = self.username.data.strip()
        u.first_name = self.first_name.data.strip()
        u.last_name = self.last_name.data.strip()
        u.email = self.email.data.strip()
        u.phone = self.phone.data.strip()
    
class ChangePassword(Form):
    old_password = PasswordField('Current Password', [DataRequired(), Regexp(ALNUM_SYMB), Length(min=5, max=30)])
    new_password = PasswordField('Change Password', [DataRequired(), Regexp(ALNUM_SYMB), Length(min=5, max=30)])
    confirm_password = PasswordField('Confirm Password', [DataRequired(), EqualTo('new_password')])
    
class AgencyForm(Form):
    name = TextField('Agency Name', [DataRequired(), Regexp(NAME_REGEX), Length(min=2, max=200)])
    address = TextField('Address', [DataRequired(), Regexp(NAME_REGEX), Length(min=2, max=200)])
    agency_type = SelectField('Agency Type', [DataRequired()], choices=[(model.Agency.DONOR, 'Donor'), 
                                                             (model.Agency.RECIPIENT, 'Recipient')])
    city = TextField('City', [DataRequired(), Regexp(NAME_REGEX), Length(min=2, max=50)])
    contact = TextField('Contact Name', [Regexp(NAME_REGEX), Length(min=0, max=200)])
    phone = TextField('Contact Phone', [Length(max=20), Regexp(r'^[\s0-9()-]*')])
    notes = TextAreaField('Notes', [Length(min=0, max=500)])
    
    def load_from_agency(self, agency):
        self.name.data = agency.name
        self.agency_type.data = agency.agency_type
        self.address.data = agency.address
        self.phone.data = agency.phone
        self.contact.data = agency.contact
        self.city.data = agency.city
        self.notes.data = agency.notes
        
        
    def load_agency(self, agency):
        agency.name = self.name.data.strip()
        agency.address = self.address.data.strip()
        agency.agency_type = self.agency_type.data
        agency.city = self.city.data.strip()
        agency.contact = self.contact.data.strip()
        agency.phone = self.phone.data.strip()
        agency.notes = self.notes.data.strip()
        
    def make_agency(self):
        a = model.Agency()
        self.load_agency(a)
        return a

class StopForm(Form):
    time = TextField('Time hh:mm\n(24 hour time)', [DataRequired(), TimeFilter()])
    
    cargo_temp = IntegerField('Cargo Temperature', [NumberRange(min=0)])
    prepared = IntegerField('Prepared', [NumberRange(min=0)])
    produce = IntegerField('Produce', [NumberRange(min=0)])
    dairy = IntegerField('Dairy', [NumberRange(min=0)])
    raw_meat = IntegerField('Raw Meat', [NumberRange(min=0)])
    perishable = IntegerField('Perishable', [NumberRange(min=0)])
    dry_goods = IntegerField('Dry Goods', [NumberRange(min=0)])
    bread = IntegerField('Bread', [NumberRange(min=0)])
    
    notes = TextAreaField('Notes', [Length(min=0, max=500)])
    
    def load_from_stop(self, stop):
        t = stop.time if stop.time else datetime.datetime.now()
        self.time.data = '%02d:%02d' % (t.hour, t.minute)
        self.bread.data = stop.bread
        self.cargo_temp.data = stop.cargo_temp
        self.dairy.data = stop.dairy
        self.raw_meat.data = stop.raw_meat
        self.perishable.data = stop.perishable
        self.dry_goods.data = stop.dry_goods
        self.prepared.data = stop.prepared
        self.produce.data = stop.produce
        self.notes.data = stop.notes
        
    def load_stop(self, stop):
        t = self.time.data.split(':')
        stop.time = datetime.time(int(t[0]), int(t[1]))
        stop.cargo_temp = self.cargo_temp.data
        stop.prepared = self.prepared.data
        stop.produce = self.produce.data
        stop.dairy = self.dairy.data
        stop.raw_meat = self.raw_meat.data
        stop.perishable = self.perishable.data
        stop.dry_goods = self.dry_goods.data
        stop.bread = self.bread.data
        stop.notes = self.notes.data.strip()
    
class AddSpecialPickup(Form):
    agency = SelectField('Add Special Stop')
    def set_choices(self, agencies):
        self.agency.choices = agencies
        
class CreateSchedule(Form):
    name = TextField('Schedule Name', [DataRequired(), Length(min=2, max=200), UniqueConstraintFilter(model.DriverSchedule, model.DriverSchedule.name)])
    