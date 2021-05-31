#! /usr/bin/env fish

set new_version 1.0.6
set new_date (date '+%Y-%m-%d')

sed -i -e "s/^\(\s*__version__\s*=\s*\).*/\1'$new_version'/g" rnr/__init__.py

for f in doc/rnr.1.adoc doc/rnrview.1.adoc
	sed -i \
		-e "s/^\(\s*:man version:\s*\).*/\1$new_version/g" \
		-e "s/^\(\s*:revdate:\s*\).*/\1$new_date/g" \
		$f
end

