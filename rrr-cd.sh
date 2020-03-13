rrr-cd() {
	local tempfile=$(mktemp -t tmp.XXXXXX)
	rrr -P "$tempfile" "$@"
	if test -f "$tempfile"; then
		local rrr_pwd=$(cat $tempfile)
		if test -n "$rrr_pwd" -a -d "$rrr_pwd"; then
			 cd -- "$rrr_pwd"
		fi

		rm -f -- "$tempfile"
	fi
}

