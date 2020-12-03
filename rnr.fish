function rnr
	set tempfile (mktemp)
	command rnr -P $tempfile $argv
	set retval $status

	if test -s $tempfile
		set rnr_pwd (cat $tempfile)
		if test -n $rnr_pwd -a -d $rnr_pwd
			cd -- $rnr_pwd
		end
	end

	command rm -f -- $tempfile

	return $retval
end

