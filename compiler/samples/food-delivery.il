Create Application FoodDelivery
  With
    Title "Fast Food Delivery"
    Frontend react
    Backend fastapi
    Database postgres

Create Role Customer
Create Role Driver

Create Model Restaurant
  Field Id
    Type id
  Field Name
    Type string
    Required true
  Field Address
    Type string
    Required true
  Field Cuisine
    Type string
    Required true
  Field Rating
    Type float
    Default 0.0
  Field IsActive
    Type boolean
    Default true

Create Model MenuItem
  Field Id
    Type id
  Field RestaurantId
    Type integer
    Reference "Restaurant.Id"
  Field Name
    Type string
    Required true
  Field Description
    Type text
  Field Price
    Type float
    Required true
  Field IsAvailable
    Type boolean
    Default true

Create Model Order
  Field Id
    Type id
  Field RestaurantId
    Type integer
    Reference "Restaurant.Id"
  Field CustomerId
    Type integer
  Field DriverId
    Type integer
  Field TotalAmount
    Type float
    Required true
  Field Status
    Type enum
    Default "Pending"
  Field CreatedAt
    Type datetime
    Required true

Create Api ListRestaurants
  With
    Method GET
    Route "/restaurants"
    Auth public

Create Api PlaceOrder
  With
    Method POST
    Route "/orders"
    Auth Customer

Create Page Home
  With
    Route "/"
    Auth public
  Add Table RestaurantList
    With
      Source Restaurant
      Columns [Name, Cuisine, Rating]

Create Page Checkout
  With
    Route "/checkout"
    Auth Customer
  Add Form OrderForm
    With
      Target Order
      Fields [TotalAmount, Status, CreatedAt]
    When Submitted
      Call Api PlaceOrder
      Navigate To Home
