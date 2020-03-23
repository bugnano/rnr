rnr() {
	local tempfile=$(mktemp)
	command rnr -P "$tempfile" "$@"
	if test -s "$tempfile"; then
		local rnr_pwd=$(cat $tempfile)
		if test -n "$rnr_pwd" -a -d "$rnr_pwd"; then
			 cd -- "$rnr_pwd"
		fi
	fi

	command rm -f -- "$tempfile"
}

