from sqlalchemy import create_engine, text

engine = create_engine('postgresql://smartcourse:password@127.0.0.1:5432/smartcourse_lms')

with engine.connect() as conn:
    conn.execute(text('DROP TABLE IF EXISTS content_chunks CASCADE'))
    conn.commit()
    print('content_chunks table dropped from LMS database')
