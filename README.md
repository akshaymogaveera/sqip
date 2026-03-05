# SQIP — Backend API & Developer Guide

This README documents back-end setup and groups the API endpoints by area (Authentication, Organizations, Categories, Appointments, OTP). It preserves example payloads and response shapes from the original doc while putting setup instructions at the top for quick onboarding.

Table of contents
- Quick setup
- Running tests
- API reference (grouped)
  - Authentication & user
  - Organizations
  - Categories
  - Appointments
  - OTP (email)
- Error formats
- Where to find code

Quick setup (recommended)
1. Create a virtual environment and activate it (recommended):

   python3 -m venv .venv
   source .venv/bin/activate

   (The repo also contains a convenience `bin/` venv that some developers use: `source bin/activate`.)

2. Install dependencies:

   pip install -r requirements.txt

3. Apply migrations and create a superuser:

   python manage.py migrate
   python manage.py createsuperuser

4. Run the dev server:

   python manage.py runserver

Running tests

  pytest -q

API reference (grouped)
Below are the commonly used endpoints grouped by functionality. For each endpoint I include URL, method, brief description and a sample request/response where helpful.

Authentication & user
---------------------

1) POST /api/auth/
- Purpose: Authenticate by phone number or username and return JWT tokens. The endpoint supports `identifier` (preferred), legacy `username`, or `phone` in the request body.
- Request examples:
  - { "identifier": "+911234567890" }
  - { "identifier": "admin_username" }
- Responses:
  - 200 OK: { status: "Success", refresh, access, id, username, first_name, last_name }
  - 400 Bad Request: { status: "Failed", message: "Phone number or username is required" }
  - 404 Not Found: { status: "Failed", message: "User not found" }

2) POST /api/register/
- Purpose: Register a new user (phone is primary identifier). Returns JWT tokens on success.
- Request example:
  {
    "first_name": "Palakh",
    "last_name": "Kanwar",
    "phone": "+911234567890",
    "email": "optional@example.com"
  }
- Notes: phone is normalized to E.164 using `phonenumbers` and must be unique.
- Response (201): tokens + user fields

3) GET /api/me/
- Purpose: Return current authenticated user's info including groups.
- Response example:
  {
    id, username, first_name, last_name, email, phone, is_staff, is_superuser, groups: [...] 
  }

4) GET /api/validate/token/ (authenticated)
- Purpose: Validate and refresh tokens. Returns new tokens when valid.

Organizations
-------------

1) GET /api/organizations/ — List organizations
- Filters: status, type, city, country, name, search across multiple fields
- Pagination supported via `?page=` and `?page_size=`.

2) GET /api/organizations/active/ — List active organizations

3) GET /api/organizations/<id>/ — Retrieve specific organization

4) GET /api/organizations/<id>/landing/ — Public landing info suitable for direct linking or QR codes

Sample organization response:
```
{
  "id": 1,
  "name": "Arfa",
  "city": "Mumbai",
  "state": "Maharashtra",
  "country": "India",
  "type": "restaurant",
  "status": "active",
  "groups": [1]
}
```

Categories
----------

1) GET /api/categories/ — List categories
- Filters: status, type, description, organization (accepts single ID or comma-separated list)

2) GET /api/categories/active/ — List active categories

3) GET /api/categories/user/ — Categories associated with the requesting user's groups

4) PATCH /api/categories/<id>/update-status/ — Toggle category status (superusers / group admins). Note: flipping a category to inactive moves its appointments to the end of the queue.

Categories example response (paginated):
```
{
  "count": 2,
  "results": [ ... ]
}
```

Appointments
------------

Common endpoints and notes for scheduling and walk-ins.

1) POST /api/appointments/unschedule/ — Create an unscheduled (walk-in) appointment
- Body: { organization: <id>, category: <id>, user: <id> }
- Response (201): appointment object including `counter` and `is_scheduled=false`.
- Error shape: validation errors are returned under `errors` (for example `{ "errors": { "appointment": ["..."] } }`).

2) POST /api/appointments/schedule/ — Create a scheduled appointment
- Note: the target `Category` must be configured with scheduling fields (opening_hours, break_hours, time_interval_per_appointment, time_zone, max_advance_days). Example payload for creating category scheduling is shown below.

3) GET /api/appointments/availability/?date=<date>&category_id=<id> — Get available slots for a date + category

4) POST /api/appointments/<id>/check-in/ — Check in an appointment

5) POST /api/appointments/<id>/checkout/ — Record checkout time (permissions apply)

6) POST /api/appointments/<id>/cancel/ — Cancel appointment (counter behavior depends on status)

7) POST /api/appointments/<id>/move/ — Move an appointment position in the queue (admin/group operations)

Scheduling example (category scheduling config):
```
{
  "time_zone": "Canada/Eastern",
  "opening_hours": {
    "Monday": [["09:00","17:00"]],
    "Tuesday": [["09:00","17:00"]],
    ...
  },
  "break_hours": {
    "Monday": [["12:00","13:00"]],
    ...
  },
  "time_interval_per_appointment": "00:15:00",
  "max_advance_days": 7
}
```

Appointments availability response example (slots with boolean available flag):
```
{
  "date": "2024-12-12",
  "slots": [ [["09:00","09:15"], false], [["09:15","09:30"], true], ... ]
}
```

OTP (email)
-----------

1) POST /api/send/otp/ — Send OTP to an email address (body: { email })
2) POST /api/verify/otp/ — Verify OTP (body: { email, otp })

Note: OTP endpoints are optional and the frontend may comment out the OTP flow per UX choices.

Error formats and conventions
----------------------------
- Validation and business errors are commonly returned under an `errors` key. For example:

  { "errors": { "appointment": ["Organization does not exist or is not accepting appointments."] } }

- Authentication errors follow DRF defaults (401 with `detail`), and some endpoints use `{ status: 'Failed', message: '...' }` for legacy flows.

Where to find code
------------------
- `main/login/views.py` — AuthenticateUser, RegisterUser, ValidateToken, OTP endpoints
- `main/appointments/views.py` & `main/appointments/service.py` — endpoints and business logic for scheduling, counters, and validation
- `main/organization/views.py`, `main/category/views.py` — organization/category CRUD and filters

Application model & relationships
---------------------------------

High-level data model and expected relationships you should know when working on the backend and frontend.

- Organization -> Categories -> Appointments
    - An `Organization` (clinic, restaurant, service provider) owns multiple `Category` records.
    - Each `Category` represents a service or queue (for example, "Walk-in", "Consultation", or "Drive-through").
    - `Appointment` belongs to an `Organization` and a `Category`. The frontend lists categories for an organization when booking.

- Status flags
    - `Organization.status` and `Category.status` are either `active` or `inactive`.
        - Inactive organizations or categories are not accepting appointments and will cause appointment creation to return a 400 error (see tests and `appointments` endpoints).
    - `Appointment.status` can be `active`, `inactive`, `checkin`, `checkout`, `cancel`, etc. Business logic in `main/appointments/service.py` controls transitions and counters.

- Appointment types
    - `is_scheduled`: boolean flag on Appointment
        - `is_scheduled = true` => scheduled appointment (requires category scheduling configuration)
        - `is_scheduled = false` => unscheduled / walk-in

- Scheduling configuration (Category)
    - To support scheduled appointments a `Category` must include scheduling configuration fields. These include `time_zone`, `opening_hours`, `break_hours`, `time_interval_per_appointment`, and `max_advance_days`.
    - `opening_hours` and `break_hours` are JSON objects keyed by weekday names. Each weekday maps to a list of time ranges (strings `HH:MM`). Example:

```
{
    "time_zone": "Asia/Kolkata",
    "opening_hours": {
        "Monday": [["09:00","17:00"]],
        "Tuesday": [["09:00","17:00"]],
        "Wednesday": [],
        "Thursday": [["10:00","16:00"]],
        "Friday": [["09:00","17:00"]],
        "Saturday": [["10:00","14:00"]],
        "Sunday": []
    },
    "break_hours": {
        "Monday": [["12:00","13:00"]],
        "Tuesday": [["12:00","13:00"]],
        "Wednesday": [],
        "Thursday": [["12:30","13:00"]],
        "Friday": [["12:00","13:00"]],
        "Saturday": [],
        "Sunday": []
    },
    "time_interval_per_appointment": "00:15:00",
    "max_advance_days": 14
}
```

    - The `appointments/availability` endpoint uses these fields to compute available time slots per date. `break_hours` ranges are treated as unavailable windows inside `opening_hours`.

- Category -> Group (permissions workflow)
    - When creating a `Category` in Django admin (or via management API) the system expects a corresponding Django `Group` to exist with the same name as the category (this project convention links categories to permission groups).
    - Typical workflow:
        1. Admin creates a `Category` and (manually or via a small admin action) creates a Django `Group` with the same name.
        2. When creating organization-level admins, the superuser assigns the appropriate `Group` to the admin user. That group membership limits the categories (and therefore appointments) the admin can see/manage.
    - This enforces a per-category visibility model: org admins see only categories associated with groups they belong to.

- Phone number uniqueness policy
    - Regular users: `Profile.phone_number` is treated as the primary identifier and must be unique (the code normalizes to E.164 before storing).
    - Admin users: it's acceptable for admin or system accounts to have a null phone number. Validation enforces uniqueness only when a phone is provided for a regular user.


Testing & Developer tips
------------------------
- Run full test-suite with pytest:

  pytest -q

- Use the `sqip` logger output to debug failing tests or requests — many views log actions and validation failures.
- If you change API error shapes or endpoint names, update tests under `main/*/tests/` accordingly.

Contributing
------------
- Keep API docs in this README in sync with code changes. If you add endpoints, list them under the appropriate group.
- Prefer backwards-compatible changes; if not possible, update tests and mention migration steps here.

Maintainers & contact
---------------------
- Check repository owners and recent committers for who to ping about PRs or design questions.

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