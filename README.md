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

> Get Appointment

URL: ```/api/appointments/<appointment_id>/``` (GET)

Sample Response:
```
{
    "id": 118,
    "type": "",
    "counter": 1,
    "status": "inactive",
    "date_created": "2024-10-27T00:31:31.327052Z",
    "is_scheduled": false,
    "estimated_time": null,
    "user": 6,
    "category": 1,
    "organization": 1,
    "created_by": null,
    "updated_by": null
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

> Check-In Appointment

URL: ```/api/appointments/<appointment_id>/check-in/``` (POST)


Sample Response:
```
{
    "detail": "Appointment status updated to 'checkin' successfully."
}
```
------------------------------------------------------------------------------------------------

> Cancel Appointment

URL: ```/api/appointments/<appointment_id>/cancel/``` (POST)


Sample Response:
```
{
    "detail": "Appointment status updated to 'cancel' successfully."
}
```
------------------------------------------------------------------------------------------------

> Move Appointment

URL: ```/api/appointments/<appointment_id>/move/``` (POST)

Request Body
```
{
    "previous_appointment_id": 2
}

If moving to first position `previous_appointment_id` will be null.

```

Sample Response:
```
{}
```
------------------------------------------------------------------------------------------------

> Get Organization

URL: ```api/organizations/<organization_id>/``` (GET)


Sample Response:
```
{
    "id": 1,
    "name": "Arfa",
    "created_by": 1,
    "portfolio_site": "",
    "display_picture": null,
    "city": "Mumbai",
    "state": "Maharashtra",
    "country": "India",
    "type": "restaurant",
    "status": "active",
    "groups": [
        1
    ]
}
```
------------------------------------------------------------------------------------------------

> List Organization

For all appointments:
    URL: ```api/organizations/``` (GET)
for active appointments:
    URL: ```api/organizations/active/``` (GET)

### Filter Examples
- `?status=active` - Filters organizations by status.
- `?type=clinic` - Filters organizations by type, such as `clinic`.
- `?city=New York` - Case-insensitive search by city name containing `New York`.
- `?country=Canada` - Case-insensitive search by country containing `Canada`.
- `?name=Arteria` - Case-insensitive search by organization name containing `Arteria`.

### Search Example
- `?search=tech` - Searches across name, city, state, country, and type fields for matches with `tech`.

### Ordering Examples
- `?ordering=name` - Orders organizations by name (ascending).
- `?ordering=-name` - Orders organizations by name (descending).
- `?ordering=city` - Orders organizations by city.
- `?ordering=state,-country` - Orders organizations by state (ascending) and country (descending).

### Pagination Examples
- `?page=1` - Returns the first page of results.
- `?page_size=5` - Adjusts the number of items per page (default is 10, maximum is 100).

### Endpoint Examples
- **Retrieve specific organization by ID**: `/organizations/<id>/`
- **List organizations with filters, search, and pagination**: `/organizations/?status=active&type=clinic&city=New York`
- **Custom action for active organizations**: `/organizations/active/` (lists organizations with `status=active`)

Sample Response:
```
{
    "count": 2,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "name": "Arfa",
            "created_by": 1,
            "portfolio_site": "",
            "display_picture": null,
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India",
            "type": "restaurant",
            "status": "active",
            "groups": [
                1
            ]
        },
        {
            "id": 2,
            "name": "Arteria AI",
            "created_by": 1,
            "portfolio_site": "",
            "display_picture": null,
            "city": "Toronto",
            "state": "ON",
            "country": "Canada",
            "type": "company",
            "status": "active",
            "groups": [
                2
            ]
        }
    ]
}
```
------------------------------------------------------------------------------------------------