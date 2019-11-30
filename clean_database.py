import t2t
import model

if __name__ == '__main__':
    with t2t.app.app_context():
        print ('Resetting the Database')
        model.reset_db()
        print ('Done')