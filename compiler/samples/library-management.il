Create Application LibraryManagementSystem
  With
    Title "Library Hub"
    Database sqlite
    Theme "#0ea5e9"

Create Role Admin
Create Role Student

Create Model Book
  Field Id
    Type id
  Field Title
    Type string
    Required true
  Field Author
    Type string
    Required true
  Field ISBN
    Type string
    Unique true
  Field TotalCopies
    Type integer
    Required true
  Field AvailableCopies
    Type integer
    Required true

Create Model Student
  Field Id
    Type id
  Field Name
    Type string
    Required true
  Field Email
    Type email
    Unique true
    Required true
  Field Password
    Type password
    Required true
  Field EnrollmentYear
    Type integer

Create Model BorrowRecord
  Field Id
    Type id
  Field BookId
    Type integer
    Reference "Book.Id"
  Field StudentId
    Type integer
    Reference "Student.Id"
  Field IssueDate
    Type date
  Field ReturnDate
    Type date
    Required false
  Field Status
    Type enum

Create Api ListBooks
  With
    Method GET
    Route /books
    Auth public

Create Api BorrowBook
  With
    Method POST
    Route /borrow
    Auth Student

Create Page Home
  With
    Route /
    Auth public
  Add Table BookList
    With
      Source Book
      Columns [Title, Author, AvailableCopies]

Create Page Login
  With
    Route /login
    Auth public
  Add Form LoginForm
    With
      Target Student
      Fields [Email, Password]
