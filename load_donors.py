from t2t import model, app
import csv
import traceback

if __name__ == "__main__":
    
        with open('in.txt', 'r') as f:
            reader = csv.reader(f, delimiter=':', quotechar='"')
            for row in reader:
                try:
                    print row
                    splt = row[0].split('\n')
                    
                    name = splt[0].strip()
                    address = splt[1].strip()
                    city = splt[2].split(',')[0].strip()
                    phone = row[1]
                    contact = row[2]
                    
                    a = model.Agency()
                    a.address = address
                    a.agency_type = model.Agency.DONOR
                    a.city = city
                    
                    name = name.replace(' ' + city, ', ' + city)
                    a.name = name
                    
                    a.contact = contact
                    a.phone = phone
                    print 'Adding'
                    with app.app_context():
                        model.db.session.add(a)
                        model.db.session.commit()
                except:
                    print traceback.format_exc()