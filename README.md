# sqip

------------------------------------------------------------------------------------------------
> Auth
api/auth/ - Get auth token using {"username": "akshay"}, Select Auth type as "No Auth"

------------------------------------------------------------------------------------------------
> Create Appointment
/api/appointments/create/ - POST

{
    "organization": 1,  # Name of Entity
    "category": 1, # Restaurant etc.
    "user":2,
    "is_scheduled": false # for unscheduled appointments, scheduled yet to be implemented.
}
------------------------------------------------------------------------------------------------