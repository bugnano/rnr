function rrr-cd
	set tempfile (mktemp -t tmp.XXXXXX)
	rrr -P $tempfile $argv
	if test -f $tempfile
		set rrr_pwd (cat $tempfile)
		if test -n $rrr_pwd -a -d $rrr_pwd
			builtin cd -- $rrr_pwd
		end

		rm -f -- $tempfile
	end
end

