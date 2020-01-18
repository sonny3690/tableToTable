# Table To Table

![Table to Table Logo](./static/t2t_logo.png)

Table to Table is a community-based food rescue program that collects perishable food that would otherwise be wasted and delivers it to organizations that serve the hungry in Bergen, Essex, Hudson and Passaic counties.

Nearly 1 million people in New Jersey are hungry, including 1 in 7 children. Every day, more families are lining up at food pantries and soup kitchens waiting for our deliveries and each week brings calls from additional agencies asking for our fresh, healthy food. To all of them, this year, we have promised the delivery of 23 million meals. Using this tool, Table to Table has served over 189 million meals.

This program runs the operation of "rescue" food from about 150 donors (supermarkets, food distributors, restaurants and commercial kitchens) and deliver it the same day free of charge to over 200 community organizations including food pantries, shelters, day care/after school programs, senior adult centers, and programs serving the working poor.

## Running the Program

Run the following to modify your scripts directory. This will give the user permissions to run our scripts.
```
chmod -R u+x ./scripts
```

Ensure you have Python3 installed.

Download `pipenv`through
```
brew install pipenv
```

Now, using the newly installed `pipenv` module:
```
pipenv shell
pipenv install
```

Make sure you have a MySQL instance running
```
./scripts/run
```


### TODO

- [x] Change query headers for load csv
- [x] Zip Code Issue (Make them a String)
- [x] Edit/New Agencies
- [x] Sort drop down on `http://0.0.0.0:5000/admin/driverrecords/4?display=5825&date=2020-01`

### Wishlist

- [ ] Drag & Drop for `http://0.0.0.0:5000/admin/editschedule/1`
- [x] `http://0.0.0.0:5000/admin/drivers/` Update Schedule Functionality for drivers account.
- [x] `Notes` field in the CSV. 
- [x] Database query by Day of Week (ie. Mon)
- [ ] Possibly display dashboard (extraneous)
- [x] 3 Accounts for Admin


