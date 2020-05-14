#    Version:   1.0
#    Date:      12/03/2019
#    Author:    Ben Loveday and Hayley Evers-King (Plymouth Marine Laboratory)
#    Credit:    This code was developed for EUMETSAT under contracts for the 
#               Copernicus programme.
#    License:   This code is offered as open source and free-to-use in the 
#               public domain, with no warranty.

from ipywidgets import widgets
from IPython.display import display

def handle_submit(sender):
    parameters = ['Mission_ID', 'Data_Source', 'Processing_Level',\
                  'Data_Type_ID', 'Sensing_Start_Time',\
                  'Sensing_End_Time', 'Creation_Date', 'Instance',\
                  'Product_Generation_Centre', 'Class_ID']
    regex = "000_11_2_333333_444444444444444_555555555555555" \
          + "_666666666666666_77777777777777777_888_99999999"

    mydict = {}    
    fname = sender.value.split('.')[0]
    for pcount in range(0,10):
        vals = [pos for pos, char in enumerate(regex) if char == str(pcount)]
        mydict[parameters[pcount]] = fname[vals[0]:vals[-1] + 1]

        if parameters[pcount] == 'Instance':
            sub_string = fname[vals[0]:vals[-1] + 1]
            print('Instance (Duration) : ' + sub_string[0:4])
            print('Instance (Cycle number) : ' + sub_string[5:8])
            print('Instance (Relative orbit number) : ' + sub_string[9:12])
            if same_chars(sub_string[13:]):
                print('Instance (Frame coordinate) : None (dump product)')                
            else:
                print('Instance (Frame coordinate) : ' + sub_string[13:])
        elif parameters[pcount] == 'Class_ID':
            sub_string = fname[vals[0]:vals[-1] + 1]
            print('Class ID (Platform) : '+sub_string[0:1])
            if 'NR' in sub_string[2:4]:
                print('Class ID (Timeliness) : NR (Near Real Time)')
            elif 'ST' in sub_string[2:4]:
                print('Class ID (Timeliness) : ST (Short time critical)')
            elif 'NT' in sub_string[2:4]:
                print('Class ID (Timeliness) : NT (Non time critical)')
            print('Class ID (Baseline collection) : ' + sub_string[5:])
        else:
            print(parameters[pcount].replace('_',' ') + ' : ' \
                + fname[vals[0]:vals[-1] + 1])

    final_string = 'This is a Sentinel-3'
    if 'A' in mydict['Mission_ID']:
        final_string = final_string + 'A '
    else:
        final_string = final_string + 'B '

    final_string = final_string + 'Level '

    if '1' in mydict['Processing_Level']:
        final_string = final_string + '1 '
    else:
        final_string = final_string + '2 '

    if 'SL' in mydict['Data_Source'] or 'MW' in mydict['Data_Source']:
        final_string = final_string + 'Surface Topography Mission '
    elif 'OL' in mydict['Data_Source']:
        final_string = final_string + 'Ocean Colour '
    else:
        final_string = final_string + 'Sea Surface Temperature '
        
    final_string = final_string + 'product'

    print('====================================================')
    print(final_string)
    print('====================================================')

def same_chars(s) : 
    n = len(s) 
    for i in range(1, n) : 
        if s[i] != s[0] : 
            return False
    return True

def text_box():
    text = widgets.Text(\
           placeholder='Please copy & paste your Sentinel-3 filename here...')
    display(text)
    text.on_submit(handle_submit)
