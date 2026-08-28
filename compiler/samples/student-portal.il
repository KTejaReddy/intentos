// =============================================================
// Student Portal — reference IntentLang program
// English  ->  AI Planner  ->  IntentLang  ->  Compiler  ->  App
// =============================================================

Create Application Student Portal
  With
    Title "Student Portal"
    Theme indigo
    Description "Portal for students to view courses and grades"
    Database sqlite

Create Role Student
  With
    Permissions [view_courses, view_grades]

// -------------------------------------------------------------
// Pages
// -------------------------------------------------------------

Create Page Login
  With
    Route /login
    Layout auth
  Add Input Username
    With
      Label "Username"
      Required true
  Add Input Password
    With
      Label "Password"
      Type password
      Required true
  Add Button "Sign In"
    When Clicked
      Call Api Login
        On Success
          Navigate To Dashboard
        On Failure
          Show Toast "Invalid credentials"

Create Page Dashboard
  With
    Route /
    Title "Dashboard"
  Add NavBar Home
  Add Text Welcome
    With
      Text "Welcome to the Student Portal"
      Variant heading
  Add Table Courses
    With
      Api GetCourses
  Add Button "Logout"
    When Clicked
      Call Api Logout
        On Success
          Navigate To Login

Create Page Profile
  With
    Route /profile
  Add Form StudentForm
    With
      Api UpdateProfile
    Add Input Name
    Add Input Email
    Add Button "Save"
      When Clicked
        Submit StudentForm
        Show Toast "Profile saved"

// -------------------------------------------------------------
// Data
// -------------------------------------------------------------

Create Database PortalDb
  With
    Engine sqlite

Create Model Student
  With
    Table students
  Field Id
    Type id
  Field Name
    Type string
    Required true
  Field Email
    Type email
    Unique true
  Field Grade
    Type string

// -------------------------------------------------------------
// APIs
// -------------------------------------------------------------

Create Api Login
  With
    Method POST
    Route /api/login
    Auth public
  Request
    Field Username
      Type string
    Field Password
      Type password
  Response
    Status 200
    Body token
    On Failure
      Status 401

Create Api GetCourses
  With
    Method GET
    Route /api/courses
    Auth student
  Query
    Select
    From students
    Order By Name
  Response
    Status 200
    Body List Student

Create Api UpdateProfile
  With
    Method PUT
    Route /api/profile
    Auth student
  Request
    Field Name
    Field Email
  Response
    Status 200
    Body Student

Create Api Logout
  With
    Method POST
    Route /api/logout
    Auth public
  Response
    Status 200

// -------------------------------------------------------------
// Global rules and deployment
// -------------------------------------------------------------

When Login succeeds
  Open Dashboard

Deploy Docker
  With
    Port 8000
