Create Application HospitalManagement
  With
    Title "Hospital Management System"
    Frontend react
    Backend fastapi
    Database postgres

Create Role Doctor
Create Role Nurse
Create Role Patient

Create Model PatientRecord
  Field Id
    Type id
  Field Name
    Type string
    Required true
  Field DOB
    Type date
    Required true
  Field Gender
    Type enum
  Field BloodType
    Type enum
  Field Contact
    Type phone
    Required true
  Field Address
    Type string
    Required true

Create Model Doctor
  Field Id
    Type id
  Field Name
    Type string
    Required true
  Field Specialty
    Type string
    Required true
  Field Department
    Type string
    Required true
  Field Availability
    Type boolean
    Default true

Create Model Appointment
  Field Id
    Type id
  Field PatientId
    Type integer
    Reference "PatientRecord.Id"
  Field DoctorId
    Type integer
    Reference "Doctor.Id"
  Field AppointmentTime
    Type datetime
    Required true
  Field Status
    Type enum
    Default "Scheduled"
  Field Notes
    Type text

Create Api ListAppointments
  With
    Method GET
    Route "/appointments"
    Auth Admin

Create Api CreateAppointment
  With
    Method POST
    Route "/appointments"
    Auth Admin

Create Page Dashboard
  With
    Route "/dashboard"
    Auth Admin
  Add Table AppointmentsTable
    With
      Source Appointment
      Columns [AppointmentTime, Status]

Create Page AddAppointment
  With
    Route "/appointments/new"
    Auth Admin
  Add Form NewAppointment
    With
      Target Appointment
      Fields [AppointmentTime, Status, Notes]
    When Submitted
      Call Api CreateAppointment
      Navigate To Dashboard
