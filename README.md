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

For all organizations:
    URL: ```api/organizations/``` (GET)
for active organizations:
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

> List Category

For all categories:
    URL: ```api/categories/``` (GET)
for active categories:
    URL: ```api/categories/active/``` (GET)


### Filter Examples
- `?status=active` - Filters categories by status.
- `?type=general` - Filters categories by type, such as `general`.
- `?description=consultation` - Case-insensitive search by description containing `consultation`.
- `?organization=<organization_id>` - Filters categories by a specific organization ID.
- `?organization=<org_id1>,<org_id2>` - Filters categories by a list of organization IDs.

### Search Example
- `?search=general` - Searches within description field for matches with `general`.

### Ordering Examples
- `?ordering=created_at` - Orders categories by creation date (ascending).
- `?ordering=-status` - Orders categories by status (descending).

### Pagination Examples
- `?page=1` - Returns the first page of results.
- `?page_size=5` - Adjusts the number of items per page (default is 10, maximum is 100).

### Endpoint Examples
- **Retrieve specific category by ID**: `/categories/<id>/`
- **List categories with filters, search, and pagination**: `/categories/?status=active&type=general&description=consultation`
- **List categories filtered by organization ID**: `/categories/?organization=1`
- **List categories filtered by multiple organization IDs**: `/categories/?organization=1,2,3`
- **Custom action for active categories**: `/categories/active/` (lists categories with `status=active`)


Sample Response:
```
{
    "count": 2,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 4,
            "name": null,
            "status": "active",
            "type": "general",
            "estimated_time": null,
            "description": "Walk in",
            "created_at": "2024-11-15T03:14:50Z",
            "group": 4,
            "organization": 3,
            "created_by": 2
        },
        {
            "id": 5,
            "name": null,
            "status": "active",
            "type": "inperson",
            "estimated_time": null,
            "description": "Drive thru",
            "created_at": "2024-11-15T03:17:07Z",
            "group": 5,
            "organization": 3,
            "created_by": 2
        }
    ]
}
```

------------------------------------------------------------------------------------------------

> List Categories under User

> Group("Tims") > user.groups = [Group("Tims")]
> Category("Tims") > category.group = Group("Tims")

URL: ```api/categories/user/``` (GET)

Can use filter same as above
?status=active


Sample Response:
```
 SAME AS ABOVE
```

------------------------------------------------------------------------------------------------

> Flip status of Category.

Will move inactive appointment to the end of the queue.
Superusers and Group Admin will have access.

URL: ```api/categories/<category-id>/update-status/``` (PATCH)

Sample body:

```
{
    "status": "inactive"
}
```


Sample Response:
```
{
    "detail": "Category status updated to active."
}
```
------------------------------------------------------------------------------------------------

> Create Unscheduled Appointment

URL: ```/api/appointments/unschedule/``` (POST)
```
{
    "organization": 1,  # Name of Entity
    "category": 1, # Restaurant etc.
    "user":2
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

> Create Scheduled Appointment

Before creating scheduled appointments, we need to create a category that has all the data present, for eg,

It should have all the necessary information like, opening hours, break hours, time_interval_per_appointment, max_advance_days
We also have some validation in place, when you fill out the opening and break hours.

Take a look below for reference.

```
{
    "id": 7,
    "name": "Arfa Sceduled - 1",
    "status": "active",
    "type": "inperson",
    "estimated_time": null,
    "description": "Dining",
    "created_at": "2024-11-26T04:56:10Z",
    "is_scheduled": true,
    "time_zone": "Canada/Eastern",
    "opening_hours": {
        "Monday": [
            [
                "09:00",
                "17:00"
            ]
        ],
        "Tuesday": [
            [
                "09:00",
                "17:00"
            ]
        ],
        "Wednesday": [
            [
                "09:00",
                "17:00"
            ]
        ],
        "Thursday": [
            [
                "09:00",
                "17:00"
            ]
        ],
        "Friday": [
            [
                "09:00",
                "17:00"
            ]
        ],
        "Saturday": [
            [
                "10:00",
                "14:00"
            ]
        ],
        "Sunday": []
    },
    "break_hours": {
        "Monday": [
            [
                "12:00",
                "13:00"
            ]
        ],
        "Tuesday": [
            [
                "12:00",
                "13:00"
            ]
        ],
        "Wednesday": [
            [
                "12:00",
                "13:00"
            ]
        ],
        "Thursday": [
            [
                "12:00",
                "13:00"
            ]
        ],
        "Friday": [
            [
                "12:00",
                "13:00"
            ]
        ],
        "Saturday": [
            [
                "12:00",
                "13:00"
            ]
        ],
        "Sunday": []
    },
    "time_interval_per_appointment": "00:15:00",
    "max_advance_days": 7,
    "group": 7,
    "organization": 1,
    "created_by": 5
}
```

Once this is done, you can use the below payload.

URL: ```/api/appointments/schedule/``` (POST)
```
{
    "user": 2,
    "category": 7,
    "organization": 1,
    "scheduled_time": "2024-12-12T16:15"
}
```

Sample Response:
```

{
    "user": 2,
    "category": 7,
    "organization": 1,
    "scheduled_time": "2024-12-12T16:15:00",
    "scheduled_end_time": "2024-12-12T16:30:00"
}

```

------------------------------------------------------------------------------------------------

> Get appointments availablity for Scheduled appointments by Date and Category

URL: ```/api/appointments/availability/?date=<date>&category_id=<id>``` (GET)

Sample resquest:
```
/api/appointments/availability/?date=2024-12-13&category_id=7
```

Sample Response:
```
{
    "date": "2024-12-12",
    "slots": [
        [
            [
                "09:00",
                "09:15"
            ],
            false
        ],
        [
            [
                "09:15",
                "09:30"
            ],
            true
        ],
        [
            [
                "09:30",
                "09:45"
            ],
            false
        ],
        [
            [
                "09:45",
                "10:00"
            ],
            false
        ],
        [
            [
                "10:00",
                "10:15"
            ],
            false
        ],
        [
            [
                "10:15",
                "10:30"
            ],
            false
        ],
        [
            [
                "10:30",
                "10:45"
            ],
            false
        ],
        [
            [
                "10:45",
                "11:00"
            ],
            false
        ],
        [
            [
                "11:00",
                "11:15"
            ],
            false
        ],
        [
            [
                "11:15",
                "11:30"
            ],
            true
        ],
        [
            [
                "11:30",
                "11:45"
            ],
            true
        ],
        [
            [
                "11:45",
                "12:00"
            ],
            true
        ],
        [
            [
                "13:00",
                "13:15"
            ],
            true
        ],
        [
            [
                "13:15",
                "13:30"
            ],
            true
        ],
        [
            [
                "13:30",
                "13:45"
            ],
            false
        ],
        [
            [
                "13:45",
                "14:00"
            ],
            false
        ],
        [
            [
                "14:00",
                "14:15"
            ],
            false
        ],
        [
            [
                "14:15",
                "14:30"
            ],
            true
        ],
        [
            [
                "14:30",
                "14:45"
            ],
            false
        ],
        [
            [
                "14:45",
                "15:00"
            ],
            true
        ],
        [
            [
                "15:00",
                "15:15"
            ],
            false
        ],
        [
            [
                "15:15",
                "15:30"
            ],
            false
        ],
        [
            [
                "15:30",
                "15:45"
            ],
            false
        ],
        [
            [
                "15:45",
                "16:00"
            ],
            true
        ],
        [
            [
                "16:00",
                "16:15"
            ],
            false
        ],
        [
            [
                "16:15",
                "16:30"
            ],
            true
        ],
        [
            [
                "16:30",
                "16:45"
            ],
            false
        ],
        [
            [
                "16:45",
                "17:00"
            ],
            true
        ]
    ],
    "available_count": 17
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
        ?type=all (default)
        ?type=scheduled
        ?type=unscheduled
        ?status=inactive
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
    ?status=inactive
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
    ?status=inactive
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

Superusers and Group Admin will have access.

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

Superusers and Group Admin and appointment creator will have access.


Sample Response:
```
{
    "detail": "Appointment status updated to 'cancel' successfully."
}
```
------------------------------------------------------------------------------------------------

> Move Appointment

URL: ```/api/appointments/<appointment_id>/move/``` (POST)

Superusers and Group Admin will have access.

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

--------------------------------------------------------------------------------------------------

> Activate Appointment

Will move inactive appointment to the end of the queue.

Superusers and Group Admin will have access.

URL: ```/api/appointments/<appointment_id>/activate/``` (POST)


Sample Response:
```
{
    "id": 134,
    "user": 7,
    "category": 1,
    "organization": 1,
    "type": "",
    "counter": 5,
    "status": "active",
    "is_scheduled": false,
    "estimated_time": null,
    "created_by": null,
    "updated_by": null
}
```
------------------------------------------------------------------------------------------------