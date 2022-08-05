#! /usr/bin/env fish

set new_version 1.0.9
set new_date (date '+%Y-%m-%d')
set new_year (date '+%Y')

sed -i -e "s/^\(\s*__version__\s*=\s*\).*/\1'$new_version'/g" rnr/__init__.py

for f in doc/rnr.1.adoc doc/rnrview.1.adoc
	sed -i \
		-e "s/^\(\s*:man version:\s*\).*/\1$new_version/g" \
		-e "s/^\(\s*:revdate:\s*\).*/\1$new_date/g" \
		$f
end

for f in (rg -l '[(]C[)] 2020-[0-9]+')
	sed -i -e "s/[(]C[)] 2020-[0-9]\+/(C) 2020-$new_year/g" $f
end

