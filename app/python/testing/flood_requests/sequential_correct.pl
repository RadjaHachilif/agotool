use strict;
use warnings;
use LWP::UserAgent;

my $caller_id = $ARGV[0];
my $url = $ARGV[1]; #"http://127.0.0.1:10110/api";

my $home_taxon_id = "9606";
my $enrichment_method = "genome";
my $fdr_cutoff =  "0.05";
my $foreground_str = "9606.ENSP00000485227%0d9606.ENSP00000365147%0d9606.ENSP00000441140%0d9606.ENSP00000378338%0d9606.ENSP00000357453%0d9606.ENSP00000262113%0d9606.ENSP00000267569%0d9606.ENSP00000269571%0d9606.ENSP00000314776%0d9606.ENSP00000356404%0d9606.ENSP00000309262%0d9606.ENSP00000315477%0d9606.ENSP00000229595%0d9606.ENSP00000454746%0d9606.ENSP00000306788%0d9606.ENSP00000256495%0d9606.ENSP00000375086%0d9606.ENSP00000483276%0d9606.ENSP00000380352%0d9606.ENSP00000426906%0d9606.ENSP00000276914%0d9606.ENSP00000304553%0d9606.ENSP00000378328%0d9606.ENSP00000398861%0d9606.ENSP00000384700%0d9606.ENSP00000310111%0d9606.ENSP00000479617%0d9606.ENSP00000383933%0d9606.ENSP00000338260%0d9606.ENSP00000263253%0d9606.ENSP00000369497%0d9606.ENSP00000268668%0d9606.ENSP00000225823%0d9606.ENSP00000380008%0d9606.ENSP00000344456%0d9606.ENSP00000385814%0d9606.ENSP00000423067%0d9606.ENSP00000300773%0d9606.ENSP00000420037%0d9606.ENSP00000448012%0d9606.ENSP00000315602%0d9606.ENSP00000364028%0d9606.ENSP00000382982%0d9606.ENSP00000399970%0d9606.ENSP00000379904%0d9606.ENSP00000267163%0d9606.ENSP00000469391%0d9606.ENSP00000305151%0d9606.ENSP00000357907%0d9606.ENSP00000410910%0d9606.ENSP00000380153%0d9606.ENSP00000174618%0d9606.ENSP00000371377%0d9606.ENSP00000476795%0d9606.ENSP00000314505%0d9606.ENSP00000254695%0d9606.ENSP00000385523%0d9606.ENSP00000429240%0d9606.ENSP00000306100%0d9606.ENSP00000397927%0d9606.ENSP00000252744%0d9606.ENSP00000340505%0d9606.ENSP00000367691%0d9606.ENSP00000336724%0d9606.ENSP00000376611%0d9606.ENSP00000423917%0d9606.ENSP00000313811%0d9606.ENSP00000430733%0d9606.ENSP00000263097%0d9606.ENSP00000426455%0d9606.ENSP00000412897%0d9606.ENSP00000257430%0d9606.ENSP00000378803%0d9606.ENSP00000231461%0d9606.ENSP00000250113%0d9606.ENSP00000377782%0d9606.ENSP00000485401%0d9606.ENSP00000232975%0d9606.ENSP00000348769%0d9606.ENSP00000324403%0d9606.ENSP00000257776%0d9606.ENSP00000361021%0d9606.ENSP00000418960%0d9606.ENSP00000355374%0d9606.ENSP00000012443%0d9606.ENSP00000276414%0d9606.ENSP00000330269%0d9606.ENSP00000225430%0d9606.ENSP00000351015%0d9606.ENSP00000384848%0d9606.ENSP00000294889%0d9606.ENSP00000367498%0d9606.ENSP00000267889%0d9606.ENSP00000243578%0d9606.ENSP00000262133%0d9606.ENSP00000370021%0d9606.ENSP00000345163%0d9606.ENSP00000349493%0d9606.ENSP00000421725";
my $background_str = "";
my $values_str = "0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0%0d0";

if ($background_str) {
    $enrichment_method = "compare_samples";
}


my $taxon = "9606";
my $ua = LWP::UserAgent->new();
my $response = $ua->post ($url,
         [taxid =>  $taxon,
         output_format => 'tsv-no-header',
         background => $background_str,
         enrichment_method => $enrichment_method,
         FDR_cutoff => '0.05',
         caller_identity => $caller_id,
         foreground => $foreground_str,
         abundance_ratio => $values_str,
         ]);
my $response_text = $response->content;
unless (defined $response_text) {
    print STDERR "CODE_ERROR #1 enrichment response_text is 'undef'\n";
    return undef;
}
my @response_lines = split("\n", $response_text);
my $number_of_lines = scalar @response_lines;
foreach my $response_line (split "\n", $response_text) {
    print "$caller_id\t$response_line\n";
}