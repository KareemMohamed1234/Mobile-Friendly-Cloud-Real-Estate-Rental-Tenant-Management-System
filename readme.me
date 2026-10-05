<h1 align="center">Real Estate Rental & Tenant Management System</h1>

Project link: https://dhueru5u.pythonanywhere.com

A mobile-friendly web application for a property company. Visitors browse available rooms, studios and apartments, book a unit and pay by bank transfer. After the manager verifies the payment, the new tenant receives a login by email and manages rent, receipts and maintenance complaints online.

Built with Python, Flask, HTML/CSS/JavaScript and Supabase (PostgreSQL, Auth, Storage).

<h2>🟦 Table of contents</h2>

Features

How it works

Tech stack

Architecture

Project structure

Data model

Getting started

Configuration

Email setup (SMTP)

Usage guide

Security

Deployment

Known limitations

<h2>🟦 Features</h2>

<h3>🔹 Visitors (no account needed)</h3>

Search available properties by type, city and maximum monthly rent

Photo gallery with thumbnails, swipe and full-screen view

Unit details: rent, deposit, bedrooms, bathrooms, capacity and description

Booking form that returns a reference such as REA-2026-A1B2C3

Bank transfer instructions with copy buttons for the IBAN and the reference

Receipt upload (image or PDF)

<h3>🔹 Tenants</h3>

Personal home page with unit details and the latest rent invoice

Rent invoices with status, bank transfer instructions and receipt upload

Payment history and printable receipts

Maintenance complaints with category, priority and a conversation thread with the manager

Confirmation of whether a repair solved the problem (Fixed closes it, Not Fixed reopens it)

Password change

<h3>🔹 Manager</h3>

Console with sidebar, live counters and a dashboard: revenue, outstanding rent, occupancy, active tenants, six-month revenue chart, unit status chart, and work queues

Buildings, properties and photo management (multi-photo upload from a phone, main photo, captions)

Payment verification: confirm or reject each transfer after checking the bank account

Tenant management: monthly invoices, tenant creation, login details sent by email

Complaint handling: status, assignee, resolution note and comments

Password reset by email link

<h2>🟦 How it works</h2>

Visitor selects a unit and books
        |
Transfers money to the company IBAN and uploads the receipt
        |
Manager checks the bank account and confirms the payment
        |
System approves the booking, reserves the unit and creates the tenant
        |
Login details are emailed to the address used for the booking
        |
Tenant logs in: rent, receipts, complaints

Only two kinds of accounts exist: manager (one fixed account) and tenant (created by the manager). There is no public sign-up.

<h2>🟦 Tech stack</h2>

Layer

Technology

Backend

Python 3, Flask

Templates and UI

Jinja2, HTML, CSS, a small amount of JavaScript

Database

Supabase PostgreSQL

Authentication

Supabase Auth (email and password)

File storage

Supabase Storage

Email

SMTP (Python smtplib)

<h2>🟦 Architecture</h2>

Browser  <--HTTPS-->  Flask app (app.py)  <--API-->  Supabase (PostgreSQL, Auth, Storage)
                             |
                             +--SMTP-->  Mail server

The browser never talks to Supabase directly. Flask is the only component that holds the Supabase keys and sends email. Row Level Security is enabled on every table with no policies, so the public key cannot read or write data.

<h2>🟦 Project structure</h2>

RealEstateApp/
├── app.py                    Server, routes, authentication, email
├── reset_manager.py          Sets the manager password in Supabase from .env
├── schema.sql                Tables, indexes, security rules, storage buckets
├── seed.sql                  Demo buildings, units, photos and one tenant
├── requirements.txt
├── .env.example              Settings template
├── static/
│   ├── css/style.css         Public site and tenant pages
│   ├── css/manager.css       Manager console
│   ├── js/app.js             Menu, copy buttons, gallery
│   └── images/
└── templates/
    ├── base.html             Public and tenant layout
    ├── manager_base.html     Manager console layout
    ├── index.html, properties.html, property_details.html
    ├── application.html, payment.html, payment_confirmation.html
    ├── login_chooser.html, auth_form.html
    ├── tenant_*.html         Tenant portal
    ├── complaint_*.html      Tenant complaint pages
    └── manager_*.html        Manager pages

<h2>🟦 Data model</h2>

Table

Purpose

buildings

Buildings or sites

properties

Rentable units: type, rent, deposit, capacity, status

property_photos

Photo gallery of each unit

applications

Booking requests from visitors

tenants

People renting a unit, with contract dates and login link

rent_invoices

One invoice per tenant per month

payments

Bank transfers waiting for or past verification

complaints

Maintenance requests

complaint_comments

Conversation thread of a complaint

complaint_attachments

Reserved for complaint photos (not used yet)

company_settings

Company and bank details (bank name, account name, IBAN, currency)

profiles

Role (tenant or manager) of each login

Property statuses: Available, Reserved, Occupied, Maintenance, Unavailable.
Complaint statuses: Open, Assigned, In Progress, Resolved - Waiting for Tenant, Closed, Reopened.

<h2>🟦 Getting started</h2>

<h3>🔹 Prerequisites</h3>

Python 3.10 or newer

A free Supabase project

A Gmail account for sending email (optional, see Email setup)

<h3>🔹 1. Clone and install</h3>

git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
cd YOUR-REPOSITORY

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

On macOS or Linux, activate with source .venv/bin/activate instead.

<h3>🔹 2. Prepare Supabase</h3>

Create a new Supabase project.

Open SQL Editor and run schema.sql. It creates the tables, security rules and the two storage buckets (property-images and receipts).

Optional: run seed.sql to load demo buildings, units, photos and a demo tenant.

Open Project Settings, API and copy the project URL, the publishable key and the secret (service role) key.

<h3>🔹 3. Configure</h3>

Copy .env.example to .env and fill in the values (see Configuration).

<h3>🔹 4. Run</h3>

python app.py

Open http://127.0.0.1:5000. On first start the manager account is created from MANAGER_EMAIL and MANAGER_PASSWORD. If you change the manager password in .env later, run python reset_manager.py to apply it to Supabase.

<h2>🟦 Configuration</h2>

All settings live in .env. Never commit this file.

Variable

Description

SUPABASE_URL

Supabase project address

SUPABASE_PUBLISHABLE_KEY

Public key, used only to check logins

SUPABASE_SERVICE_KEY

Secret server key. Never share it.

FLASK_SECRET_KEY

Long random string that signs sessions and reset links

MANAGER_EMAIL

Email of the single manager account

MANAGER_PASSWORD

Password for that account, at least 8 characters

MANAGER_NAME

Display name of the manager

SMTP_HOST, SMTP_PORT

Mail server, for example smtp.gmail.com and 587

SMTP_USER, SMTP_PASSWORD

Mail account and its app password

SMTP_FROM

Sender address, normally the same as SMTP_USER

MAIL_FROM_NAME

Sender name shown in emails

SITE_URL

Public address of the site, used for links in emails

Generate a secret key with:

python -c "import secrets; print(secrets.token_hex(32))"

<h2>🟦 Email setup (SMTP)</h2>

The app sends two emails: the tenant's login details and the manager's password reset link.

With Gmail:

Turn on 2-Step Verification for the account.

Create an app password at https://myaccount.google.com/apppasswords.

Put it in SMTP_PASSWORD without spaces and set SMTP_USER and SMTP_FROM to the Gmail address.

Restart the server after editing .env.

If SMTP is not configured the app keeps working. The manager sees a notice with the tenant's login to pass on, and the reset link is printed in the server log.

<h2>🟦 Usage guide</h2>

As a visitor: search on the home page, open a unit, press the booking button, fill in the form, transfer the amount to the shown IBAN and upload the receipt.

As the manager: log in at /login/manager.

Open Payments and check each receipt against the bank account, then Confirm or Reject.

Confirming approves the booking, reserves the unit, creates the tenant and emails the login.

Open Tenants to create monthly invoices, add tenants manually, or resend login details with a new password.

Open Properties to add units and upload photos.

Open Complaints to assign, update and comment.

As a tenant: log in at /login/tenant with the emailed credentials, change the password, pay rent by transfer and upload receipts, and report problems.

<h2>🟦 Security</h2>

Row Level Security is on for every table. Only the server, using the secret key, can access data.

Passwords are hashed by Supabase Auth. Generated tenant passwords use Python's secrets module.

Routes are guarded by role. Tenants see only their own invoices, payments, complaints and receipts.

Receipts are stored in a private bucket and opened through short-lived signed links.

The manager reset link is signed, expires after 30 minutes and works once.

Uploads are limited to images and PDFs, and redirect targets are validated.

.env is listed in .gitignore. Keep your keys and passwords out of the repository.

<h2>🟦 Deployment</h2>

The built-in server is for development only. For production:

Install a production server, for example pip install gunicorn, and start it with gunicorn app:app.

Set all variables from the table above in the host's environment settings instead of a file.

Set SITE_URL to the public address of the site.

Use a stable FLASK_SECRET_KEY.

Serve the site over HTTPS.

<h2>🟦 Known limitations</h2>

Payment confirmation and booking approval are one action.

Rent invoices are created manually, and nothing marks an invoice overdue automatically.

Visitors cannot track a booking after the confirmation page.

The photo field on the complaint form is not saved yet.

Bank details are edited in the company_settings table in Supabase, there is no settings page.

Demo photos are sample images from Unsplash. Replace them with your own through the manager console.