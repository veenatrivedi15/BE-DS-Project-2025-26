# Role-Based Access Control Implementation

This document outlines the role-based access control (RBAC) system implemented in the Carbon Credits application.

## User Roles

The system supports the following user roles:

- **Super Admin**: Highest level of access, can manage system configurations and all other functions
- **Bank Admin**: Can approve employers, verify trips, and has access to administrative functions
- **Employer**: Can manage their employees, view trip statistics, and participate in the carbon credit marketplace
- **Employee**: Can record trips, earn carbon credits, and view their own statistics

## Permission Classes

### Users App Permissions

Located in `users/permissions.py`:

- `IsSuperAdmin`: Only allows super admin users
- `IsBankAdmin`: Allows bank admins and super admins
- `IsEmployer`: Allows employers, bank admins, and super admins
- `IsEmployee`: Allows employees, employers, bank admins, and super admins
- `IsOwnerOrAdmin`: Allows owners of objects and admins
- `IsApprovedUser`: Restricts access to approved users only

### Trips App Permissions

Located in `trips/permissions.py`:

- `IsOwnerOrAdmin`: Permits trip owners or admins to access a trip
- `IsEmployerOrAdmin`: Permits employers or admins
- `IsEmployeeOrEmployerOrAdmin`: Permits employees (for their own trips), employers (for their employees' trips), or admins
- `IsCreditOwnerOrAdmin`: Permits carbon credit owners or admins

### Marketplace App Permissions

Located in `marketplace/permissions.py`:

- `IsEmployerOrAdmin`: Permits employers or admins to access marketplace features
- `IsOfferParticipantOrAdmin`: Permits participants in a transaction (buyer or seller) or admins
- `IsOfferSellerOrAdmin`: Permits only the seller of an offer or admins to modify it

## View Access Controls

### User Management

- Registration is allowed for all users (AllowAny)
- User profiles are restricted based on ownership and role hierarchy
- Employer approval is restricted to bank admins and super admins
- Employee approval is restricted to their employers, bank admins, and super admins

### Trip Management

- Trip creation is restricted to employees
- Trip details are restricted to the trip owner, their employer, or admins
- Trip verification is restricted to bank admins and super admins
- Trip statistics are available to the trip owner, their employer, or admins

### Carbon Credits

- Credit listing is restricted based on ownership hierarchy
- Credit statistics are available to credit owners, their employers, or admins
- Employer-wide credit statistics are restricted to employers, bank admins, and super admins

### Marketplace

- Market offers can only be created by employers
- Market offer cancellation is restricted to the offer seller or admins
- Transaction approval/rejection is restricted to the seller or admins
- Market statistics are available to employers, bank admins, and super admins

### System Administration

- System configuration management is restricted to super admins
- Admin dashboard statistics are available to bank admins and super admins

## Approval Workflow

1. New users register with the system
2. Super admins and bank admins can approve employer accounts
3. Employers can approve employee accounts
4. Only approved users can access the system features according to their role

## Object-Level Permissions

In addition to view-level permissions, the system implements object-level permissions to ensure that users can only access or modify objects they own or have authority over:

- Employees can only access their own trips and credits
- Employers can access their own profile and their employees' profiles, trips, and credits
- Marketplace participants can only access transactions they're involved in
- Sellers can only cancel their own market offers and approve/reject transactions for their offers 