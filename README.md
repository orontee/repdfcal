# reMarkable PDF calendar

Page-per-day calendar, generated for reMarkable tablet.

French school and bank holidays can be included.

This project is a fork of [pdfcal](https://github.com/osresearch/pdfcal).


![First page view](./first_page_view.jpg)

## Build calendar

Initialize build env and generate:

``` shell
$ python -m venv env
$ source env/bin/activate
(env)$ python -m pip install .
(env)$ python -m repdfcal --year 2026
Generation of calendar for 2026
Writing agenda-2026.pdf
```

To include French school and bank holidays, set current locale to
`fr_FR` and specify a zone for the school holidays (`--school-zone`)
and/or a bank holiday zone (`--bank-holidays`):

``` shell
(env)$ python -m repdfcal --year 2026 --school-zone C --bank-holidays Métropole
Generation of calendar for 2026
Collecting French holidays
Writing agenda-2026.pdf
```
