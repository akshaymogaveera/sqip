# sqip

------------------------------------------------------------------------------------------------
> Auth
Get auth token, Select Auth type as "No Auth"

URL: ```api/auth/``` (POST)
Body
```
{"username": "test"}
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

URL: ```/api/appointments/create/``` (POST)
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

> List Appointment

URL: ```/api/appointments/``` (GET)

Query parameters
```
        ?status_filter=all (default)
        ?status_filter=scheduled
        ?status_filter=unscheduled
```

Sample Response:
```
{
    "count": 2,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 126,
            "type": "",
            "counter": 5,
            "status": "active",
            "date_created": "2024-11-03T00:52:12.463655Z",
            "is_scheduled": false,
            "estimated_time": null,
            "user": 3,
            "category": 1,
            "organization": 1
        },
        {
            "id": 127,
            "type": "",
            "counter": 1,
            "status": "active",
            "date_created": "2024-11-03T00:52:37.484204Z",
            "is_scheduled": false,
            "estimated_time": null,
            "user": 3,
            "category": 2,
            "organization": 2
        }
    ]
}
```
------------------------------------------------------------------------------------------------

> List Unscheduled Appointment

URL: ```/api/appointments/unscheduled/``` (GET)

Query parameters
```
    ?category_id=1&category_id=2&category_id=3 (filter by categories)
```

Sample Response:
```
{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 126,
            "type": "",
            "counter": 5,
            "status": "active",
            "date_created": "2024-11-03T00:52:12.463655Z",
            "is_scheduled": false,
            "estimated_time": null,
            "user": 3,
            "category": 1,
            "organization": 1
        }
    ]
}
```
------------------------------------------------------------------------------------------------

> List Scheduled Appointment

URL: ```/api/appointments/scheduled/``` (GET)

Query parameters
```
    ?category_id=1&category_id=2&category_id=3 (filter by categories)
```

Sample Response:
```
{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 126,
            "type": "",
            "counter": 5,
            "status": "active",
            "date_created": "2024-11-03T00:52:12.463655Z",
            "is_scheduled": true,
            "estimated_time": null,
            "user": 3,
            "category": 1,
            "organization": 1
        }
    ]
}
```
------------------------------------------------------------------------------------------------