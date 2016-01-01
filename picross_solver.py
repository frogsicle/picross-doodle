import getopt
import sys
import os.path

def usage():
    usagestr = """ python picros_solver.py -p path/to/rules [options]
###############
-p | --path=            path to directory with columns.txt and rows.txt (comma separated rules)
-h | --help             prints this message
"""
    print(usagestr)
    sys.exit(1)

def read_rules(filein):
    out = []
    lines = open(filein).readlines()
    for line in lines:
        line = line.rstrip()
        line = line.split(',')
        line = [int(x) for x in line]
        out.append(line)
    return out

def fit_remaining(n, remaining_rule):
    out = []
    # if length rule == length remaining, return
    min_length = get_min_length(remaining_rule)
    current_rule = remaining_rule[0]
    if len(remaining_rule) == 1:
        for pos in range(n - remaining_rule[0] + 1):
            prefix = [0 for x in range(pos)]
            run = [1 for x in range(current_rule)]
            suffix = [0 for x in range(n - pos - current_rule)]
            out.append(prefix + run + suffix)
    # call self with possible positions for first rule element
    else:
        new_remaining_rule = remaining_rule[1:]
        new_n = n - remaining_rule[0] - 1
        for offset in range(0, n - min_length + 1):
            prefix = [0 for x in range(offset)]
            run = [1 for x in range(current_rule)]
            spacer = [0]  # there's probably a better way to get [0, 0, ..., 0]
            remaining_possibilities = fit_remaining(n=new_n - offset, remaining_rule=new_remaining_rule)
            #remaining_possibilities = [[1,1,0,0,1,1],[1,1,0,1,1,0], [0,1,1,0,1,1]]
            # concatenate to results and return
            for possibility in remaining_possibilities:
                out.append(prefix + run + spacer + possibility)
    return out

    # calculate remaining space
    # take first element and assign possible positions
        # take next element and assign possible positions
    # when it's the last element, assign possible positions and return

def min_rule(rule):
    # deprecated?
    out = []
    for runs in rule:
        out += [1 for x in range(runs)]
        out.append(0)  # 0's for the spaces in between
    out.pop()  # remove last '0' because it's no longer in between
    return out


def get_min_length(rule):
    y = 0
    for x in rule:
        y += x
    y += (len(rule) - 1)
    return y

def fixwidth(string, width):
    string = str(string)
    string = string + " " * (width - len(string))
    return (string)

class Board():
    spacing = 3

    def __init__(self, board_path='.'):
        self.columns = []
        self.rows = []
        col_rules = read_rules(board_path + '/columns.txt')
        row_rules = read_rules(board_path + '/rows.txt')
        for rule in col_rules:
            self.columns.append(Column(rule=rule, n=len(row_rules)))
        for rule in row_rules:
            self.rows.append(Row(rule=rule, n=len(col_rules)))
        self.row_constraints = []
        self.col_constraints = []
        if os.path.isfile(board_path + '/seeds.txt'):
            self.add_seed(board_path + '/seeds.txt')

    def __str__(self):
        col_space = max([len(x.rule) for x in self.columns])
        str_col_rules = [self.rules_by_index(x) for x in range(col_space)]

        row_space = max([len(x.rule) for x in self.rows])
        row_prefix = ' ' * (row_space * self.spacing)
        lines = []
        for i in range(col_space):
            lines.append(row_prefix + str_col_rules[i])
        for row in self.rows:
            with_space = [fixwidth(x, self.spacing) for x in row.rule]
            lines.append(''.join(with_space))
        return('\n'.join(lines))

    def rules_by_index(self, i):
        out = []
        for column in self.columns:
            try:
                rule_of_i = str(column.rule[i])
            except IndexError:
                rule_of_i = ""
            rule_of_i = fixwidth(rule_of_i, self.spacing)
            out.append(rule_of_i)
        out = "".join(out)
        return out

    def set_row_constraints(self):
        col_summaries = []
        for col in self.columns:
            try:
                col_summaries.append(col.summarize())
            except IndexError:
                print col
                raise Exception('meh')

        self.row_constraints = []
        for row_index in range(len(self.rows)):
            try:
                self.row_constraints.append([csum[row_index] for csum in col_summaries])
            except:
                print(row_index)
                print(col_summaries)

    def set_col_constraints(self):
        row_summaries = []
        for row in self.rows:
            row_summaries.append(row.summarize())

        self.col_constraints = []
        for col_index in range(len(self.columns)):
            self.col_constraints.append([rsum[col_index] for rsum in row_summaries])

    def drop_invalid_by_row(self):
        for i in range(len(self.row_constraints)):
            self.rows[i].drop_invalid(self.row_constraints[i])

    def drop_invalid_by_column(self):
        for i in range(len(self.col_constraints)):
            self.columns[i].drop_invalid(self.col_constraints[i])

    def drop_invalid(self):
        self.drop_invalid_by_row()
        self.drop_invalid_by_column()

    def add_seed(self, seed_file):
        # read in and clean seeds from file
        seed_rows = open(seed_file).readlines()
        clean_seed_rows = []
        for line in seed_rows:
            clean_line = line.rstrip()
            clean_line = list(clean_line)
            for i in range(len(clean_line)):
                try:
                    clean_line[i] = int(clean_line[i])
                except ValueError:
                    clean_line[i] = '?'
            clean_seed_rows.append(clean_line)
        seed_rows = clean_seed_rows
        # transpose for columns
        seed_cols = []
        for i in range(len(seed_rows[0])):
            new_seed_col = [x[i] for x in seed_rows]
            seed_cols.append(new_seed_col)
        # constrain possibilities based on seeds
        self.row_constraints = seed_rows
        self.col_constraints = seed_cols
        self.drop_invalid()
        self.row_constraints = self.col_constraints = [] # reset, just in case it's used elsewhere

    def is_finished(self):
        n_arrangements_remaining = [len(x.potentials) for x in self.rows + self.columns]
        out = False
        if max(n_arrangements_remaining) == 1:
            out = True
        return out


class BlockSet():
    def __init__(self, rule, n):
        self.n = n
        self.rule = rule
        self.potentials = fit_remaining(n, self.rule)
        self.drop_redundant()

    def drop_invalid(self, constraints):
        for i in range(len(self.potentials) - 1, -1, -1):  # that's [n - 1, n - 2, ..., 0]
            potential = self.potentials[i]
            pos = 0
            while pos < self.n:
                if potential[pos] != constraints[pos] and constraints[pos] != "?":
                    self.potentials.pop(i)
                    pos = self.n
                pos += 1

    def drop_redundant(self):
        # necessary for the '0' rule case
        self.potentials = list(set(map(tuple, self.potentials)))

    def summarize(self):
        out = []
        for i in range(self.n):
            options = [x[i] for x in self.potentials]
            set_options = set(options)
            options = list(set_options)
            if len(options) > 1:
                out.append('?')
            else:
                out.append(options[0])
        return out

    def __str__(self):
        n = 'n: ' + str(self.n) + '\n'
        rule = 'rule: ' + str(self.rule) + '\n'
        opts = 'possibilities: ' + str(self.potentials) + '\n'
        return n + rule + opts

    def str_done(self):
        listout = ['.' for x in range(self.n)]
        for i in range(len(self.potentials[0])):
            box = self.potentials[0][i]
            if box:
                listout[i] = '#'
        out = ''.join(listout)
        return out


class Row(BlockSet):
    pass

class Column(BlockSet):
    pass

def main():
    board_path = '.'
    # get opt
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "p:h", ["path=", "help"])
    except getopt.GetoptError as err:
        print (str(err))
        usage()

    for o, a in opts:
       if o in ("-p", "--path"):
           board_path = a
       elif o in ("-h", "--help"):
           usage()
       else:
           assert False, "unhandled option"

    # running
    board=Board(board_path)
    counter = 0
    while not board.is_finished():
        board.set_col_constraints()
        board.set_row_constraints()
        board.drop_invalid()
        counter +=1

    # reporting
    print('setup:\n' + str(board) + '\n')
    print('solution:\n')
    for r in board.rows:
        print r.str_done()
    print '\nrounds taken: ' + str(counter) + '\n'

if __name__ == "__main__":
    main()
