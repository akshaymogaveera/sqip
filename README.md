# sqip

------------------------------------------------------------------------------------------------
> Auth
api/auth/ - Get auth token, Select Auth type as "No Auth"

Body
```
{"username": "akshay"}
```

Sample Response:
```
{
    "status": "Success",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTczMDA3ODU5MywiaWF0IjoxNzI5OTkyMTkzLCJqdGkiOiI3ZGI2YzEyZGU2ZmQ0MTY1YjI1MDk0MjdkMDdiN2RjYiIsInVzZXJfaWQiOjN9.y7jA6YeAzXjOi0xmJ0VX9Vjj2mEV3WsbS3xiw0VL8zc",
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzMwMTAwMTkzLCJpYXQiOjE3Mjk5OTIxOTMsImp0aSI6IjdlMjU2NDY5OWIzZjQ0ZmViNjFkNjZjMGNiYTNiMzQyIiwidXNlcl9pZCI6M30.ERsw_zENrK0ZkpUOb2wyQHFGJM7N9IW25tQyhdMKN58",
    "id": 3,
    "username": "test"
}
```


------------------------------------------------------------------------------------------------
> Create Appointment
/api/appointments/create/ - POST

```
{
    "organization": 1,  # Name of Entity
    "category": 1, # Restaurant etc.
    "user":2,
    "is_scheduled": false # for unscheduled appointments, scheduled yet to be implemented.
}
```

Sample Response:
```
{
    "id": 119,
    "user": 4,
    "category": 1,
    "type": "",
    "organization": 1,
    "status": "active",
    "date_created": "2024-10-27T01:23:53.361025Z",
    "counter": 2,
    "is_scheduled": false,
    "estimated_time": null
}
```
------------------------------------------------------------------------------------------------
