#!/usr/bin/env python2.7
"""
parallelMappingEvaluation.py: Run the mapping evaluation on all the servers in
parallel.

BAM files with reads must have been already downloaded.

"""

import argparse, sys, os, os.path, random, subprocess, shutil, itertools, glob
import doctest

import jobTree.scriptTree.target
import jobTree.scriptTree.stack
import sonLib.bioio



def parse_args(args):
    """
    Takes in the command-line arguments list (args), and returns a nice argparse
    result with fields for all the options.
    
    Borrows heavily from the argparse documentation examples:
    <http://docs.python.org/library/argparse.html>
    """
    
    # Construct the parser (which is stored in parser)
    # Module docstring lives in __doc__
    # See http://python-forum.com/pythonforum/viewtopic.php?f=3&t=36847
    # And a formatter class so our examples in the docstring look good. Isn't it
    # convenient how we already wrapped it to 80 characters?
    # See http://docs.python.org/library/argparse.html#formatter-class
    parser = argparse.ArgumentParser(description=__doc__, 
        formatter_class=argparse.RawDescriptionHelpFormatter)
    
    # General options
    parser.add_argument("server_list", type=argparse.FileType("r"),
        help="TSV file continaing <region>\t<url> lines for servers to test")
    
    # Add the jobTree options
    jobTree.scriptTree.stack.Stack.addJobTreeOptions(parser)
    
    # The command line arguments start with the program name, which we don't
    # want to treat as an argument for argparse. So we remove it.
    args = args[1:]
        
    return parser.parse_args(args)
    
def run_all_alignments(target, server_list):
    """
    For each server listed in the server_list tsv, kick off child targets to
    align and evaluate it.

    """

    # Make sure we skip the header
    is_first = True
    
    for line in server_list:
        if is_first:
            # This is the header, skip it.
            is_first = False
            continue
        
        # We need to read each non-header line
        
        # Break it into its fields
        parts = line.split("\t")
        
        if(parts[0].startswith("#")):
            # Skip comments
            continue
    
        # We cleverly just split the lines out to different nodes
        target.addChildTarget(RunAlignmentTarget(line))
            
        # Say what we did
        target.logToMaster("Running child for {}".format(parts[1]))
        
class RunAlignmentTarget(jobTree.scriptTree.target.Target):
    """
    A target that runs a single server's alignment. Has to be a class since
    target function targets get their CPU and memory ignored.
    
    """
    
    def __init__(self, line):
        """
        Save the argument
        
        """
        
        # Make the base Target. Request a whole ku machine
        super(RunAlignmentTarget, self).__init__(memory=240 * 2 ** 30, cpu=32)
        
        # Save argument
        self.line = line
        
    def run(self):
        """
        For the given line of the server list TSV, run the alignment and evaluate
        it.
        
        """

        print("Have {} memory, {} cpus".format(self.getMemory(), self.getCpu()))

        # We cleverly cheat by just running our own personal instance of the
        # mapping_evaluation.sh script, so all the real work is still done in bash
        script = subprocess.Popen(["./mapping_evaluation.sh"],
            stdin=subprocess.PIPE)
        
        # Send it a fake first line for it to skip, and then the actual data.
        script.stdin.write("fake_header\n" + self.line)
        script.stdin.close()
        script.wait()
        
        if script.returncode != 0:
            # Fire off an error message
            message = "Error: process on {} died with code {}".format(
                self.line.strip(), script.returncode)
                
            self.logToMaster(message)
            raise RuntimeError(message)
            
        self.logToMaster("Finished: {}".format(self.line.strip()))
    
def main(args):
    """
    Parses command line arguments and do the work of the program.
    "args" specifies the program arguments, with args[0] being the executable
    name. The return value should be used as the program's exit code.
    """
    
    if len(args) == 2 and args[1] == "--test":
        # Run the tests
        return doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
    
    options = parse_args(args) # This holds the nicely-parsed options object
    
    if __name__ == "__main__" :
        # Re-import functions
        from parallelMappingEvaluation import run_all_alignments, \
            RunAlignmentTarget
    
    # Make a stack of jobs to run, starting with all our arguments.
    stack = jobTree.scriptTree.stack.Stack(
        jobTree.scriptTree.target.Target.makeTargetFn(
        run_all_alignments, (list(options.server_list),), memory=2 * 2 ** 30,
        cpu=1))
    
    print "Starting stack"
    
    # Run it and see how many jobs fail
    failed_jobs = stack.startJobTree(options)
    
    if failed_jobs > 0:
        raise Exception("{} jobs failed!".format(failed_jobs))
        
    print "All jobs completed successfully"
    
if __name__ == "__main__" :
    sys.exit(main(sys.argv))
        
        
        
        
        
        
        
        
        
        

