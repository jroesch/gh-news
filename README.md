# TVM News

A tool for generating the TVM newsletter's detailed statistics.
The initial version of this tool was written by
[Ziheng Jiang](https://github.com/ZihengJiang).
In order to make it more discoverable and reusable I packaged it
as a poetry package and made some updates and additions.
If you already have Poetry installed you can run the tool like
so `poetry run gh-news <args>`.

For supported arguments check `poetry run gh-news --help`.

You can generate the results for a single month using this
command: `poetry run gh-news --year 2020 --month 1`.

The command now caches the results of scrapping GitHub,
if you want to tweak the template or format, you can
quickly re-run the script to regenerate the report.
