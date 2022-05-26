from datetime import datetime, date, timedelta
from statistics import mode
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from lakey_client import LakeyStreamlitClient, EQ, LTE, GTE, AND, GROUP, OR, LEFT_PAR, RIGHT_PAR
import time
import numpy as np
import plotly.express as px
from pykalman import KalmanFilter
import json


# Example:
    # start = "2022-03-21T12:42"
    # end = "2022-03-27T12:43"
    # gateway_id = "7633107166549211"

    # gateway_id ="7571381809216109" For presentation


    #some_problems = 7571381619270209
#To do:
#Checkbox Wi-Fi v
#End date not later than today v
#Download Wi-Fi signal data v
#Wi-Fi graph v
#Better interpretation (last 3 days to anlyze) v
#Generate report v




LakeyStreamlitClient.create(st)
lakey = st.session_state["lakey"]
st.header("Availability")
@st.experimental_memo()
def fetch_data(gateway_id,start,end):
    result = lakey.download(
        catalogue_item_id=12,
        columns=[
            "gateway_id",
            "start",
            "end",
            "installation_id",
            "boiler_id",
            "connected_hours",
            "availability",
            "topology_hash",
        ],
        filters=[
            EQ("gateway_id", gateway_id),
            GTE("start", start),
            LTE("end", end),
        ],
        distinct=False,
        count=False,
        limit=None)
    return result["data"]
@st.experimental_memo()
def fetch_signal(gateway_id, start, end):
    date_filters = []
    for days in range((end - start).days + 1):
        d = start + timedelta(days=days)
        date_filters.append(GROUP(
            EQ('year', d.year),
            AND(),
            EQ('month', d.month),
            AND(),
            EQ('day', d.day),
        ))
        if d != end:
            date_filters.append(OR())
    result=lakey.download(
        catalogue_item_id=7,
        columns=[
            "timestamp_client",
            "value",
        ],
        filters=[
            EQ("property", "gateway.wifi/strength"),
            EQ("gateway_id", gateway_id),
            LEFT_PAR(),
            *date_filters,
            RIGHT_PAR(),
        ],
        distinct=False,
        count=False,
        limit=None)
    return result["data"]
def choose_quicktime_option():
    with st.expander("Quickselect time"):
        options = ["last week", "last two weeks", "last month", "last two months"]
        option = st.radio("Time periods:", options)
        if not option:
            option = 2
        elif option == "last week":
            option = 7
        elif option == "last two weeks":
            option = 14
        elif option == "last month":
            option = 30
        elif option == "last two months":
            option = 60
        return option
def format_date(d, end_of_day=False):
    if end_of_day:
        hour = "23:59:59.999Z"
    else:
        hour = date.today().strftime("%H:%M")
    return str(d) + "T" + hour
if st.session_state["token"] and lakey:
    with st.form("dates_and_wifi"):
        gateway_id = st.text_input("Insert gateway id:")

        text=""
        text1=""
        option = choose_quicktime_option()
        
        start = st.date_input(
            "Start time:",
            datetime.now() - timedelta(days=option),
            max_value=datetime.now() - timedelta(days=1))
        end = st.date_input(
            "End time:",
            datetime.now(),
            max_value=datetime.now())
        check_wifi = 0
        if st.checkbox("Attach data about Wi-Fi strength signal"):
            check_wifi = 1
        submitted = st.form_submit_button("Submit")
        if submitted:
            st.session_state["submitted"] = True
    if st.session_state.get("submitted"):
        df = fetch_data(
            gateway_id,
            format_date(start),
            format_date(end, end_of_day=True)
        ).sort_values(by=["start"])
        last_3days = (end - timedelta(days=3)).isoformat()
        last_3days_filttered = df.loc[df["start"] > last_3days, ['availability']].values
        #st.write(last_3days_filttered)
        availabilityround = np.round(last_3days_filttered, 3)
        #st.write(availabilityround)
        if any(x < 0.9 for x in availabilityround):
            text="There are some problems with the availability of this device !"
            comm = st.error(text)
        else:
            text="No problem with availability on this device"
            comm = st.success(text)
        if check_wifi == 1:
            sf = fetch_signal(gateway_id, start, end).sort_values(by=["timestamp_client"])
            kf = KalmanFilter(transition_matrices=[1],
                            observation_matrices=[1],
                            initial_state_mean=sf["value"].values[0],
                            initial_state_covariance=1,
                            observation_covariance=1,
                            transition_covariance=.01)
            sf["value"] = sf["value"].astype(float)

            last_3days_wifi = (end - timedelta(days=3)).isoformat()
            last_3days_filttered_wifi = sf.loc[sf["timestamp_client"] > last_3days_wifi, ['value']].values
            #st.write(last_3days_filttered_wifi)

            signals = kf.filter(last_3days_filttered_wifi)
            avgsignal = mode(signals[0].flatten())
            #st.write(avgsignal)


            if (int(avgsignal)) > -87 and (int(avgsignal)) < -67:
                text1="Wi-Fi strength signal of this device is weak.Strengthen the signal is recommended."
                comm1 = st.warning(text1)
            elif (int(avgsignal)) <= -87:
                text1 = "Wi-Fi strength signal of this device is weak.Strengthen the signal is recommended."
                comm1 = st.error(text1)
            elif (int(avgsignal)) >= -67 and (int(avgsignal)) < -57:
                text1="Wi-Fi strength signal of this device is Ok"
                comm1 = st.info(text1)
            elif (int(avgsignal)) >= -57:
                text1="Wi-Fi strength signal of this device is very good"
                comm1 = st.success(text1)

        st.subheader("Device availability in last week:")
        diff_time= (end - start)
        days=diff_time.days
        #st.write(days)
        time_intervals=[]
        time_intervals1 = ("all data","last 3 days", "last 5 days", "last week", "last two weeks","last three weeks","last month","last three months","last six months","last year")
        choice=0
        end_interval=0
        if days >= 3 :
            time_intervals.append(time_intervals1[end_interval])
            end_interval += 1
            if days >3:
                time_intervals.append(time_intervals1[end_interval])
            if days >= 5 :
                end_interval += 1
                time_intervals.append(time_intervals1[end_interval])
            if days >= 7 :
                end_interval += 1
                time_intervals.append(time_intervals1[end_interval])
            if days >= 14:
                end_interval += 1
                time_intervals.append(time_intervals1[end_interval])
            if days >= 21:
                end_interval += 1
                time_intervals.append(time_intervals1[end_interval])
            if days >= 30:
                end_interval += 1
                time_intervals.append(time_intervals1[end_interval])
            if days >= 90:
                end_interval += 1
                time_intervals.append(time_intervals1[end_interval])
            if days >= 182:
                end_interval += 1
                time_intervals.append(time_intervals1[end_interval])
            if days >= 365:
                end_interval += 1
                time_intervals.append(time_intervals1[end_interval])
            #st.write(time_intervals)
            if days >=4:
                choice = st.selectbox("Select your time interval", time_intervals)
            if choice == "last 3 days":
                choice = 3
            if choice == "last 5 days":
                choice = 5
            if choice == "last week":
                choice = 7
            if choice == "last two weeks":
                choice = 14
            if choice == "last three weeks":
                choice = 21
            if choice == "last month":
                choice = 30
            if choice == "last three months":
                choice = 90
            if choice == "last six months":
                choice = 182
            if choice =="last year":
                choice = 365
            if choice == "all data":
                choice=days
            fig = px.bar(x=df["start"].iloc[-choice:], y=df["availability"].iloc[-choice:] *100,
                        labels=dict(x="Day", y="Availability[%]"))

            fig.update_layout(yaxis_range=[0, 100])
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df[["start", "end", "connected_hours", "availability"]])
        csv = df[["start", "end", "connected_hours", "availability"]].to_csv().encode('utf-8')
        if  st.download_button(
            label="Click to download table as CSV file.",
            data=csv,
            file_name='Availability ' + gateway_id + '.csv',
            mime='text/csv',
        ):
            st.session_state["submitted"] = True

        wifi_for_last_3days = ""

        if check_wifi == 1:
            st.subheader("Wi-Fi Signal Strength:")



            kf = KalmanFilter(transition_matrices=[1],
                              observation_matrices=[1],
                              initial_state_mean=sf["value"].values[0],
                              initial_state_covariance=1,
                              observation_covariance=1,
                              transition_covariance=.01)
            signals = kf.smooth(sf["value"])
            if st.checkbox("Kalman Filter"):
                fig1 = px.line(x=sf["timestamp_client"], y=signals[0].flatten(),
                               labels=dict(x="Day", y="Wi-Fi Strength[dBm]"))

                st.plotly_chart(fig1, use_container_width=True)
            else:
                fig1 = px.line(x=sf["timestamp_client"], y=sf["value"],
                               labels=dict(x="Day", y="Wi-Fi Strength[dBm]"))

                st.plotly_chart(fig1, use_container_width=True)
            st.dataframe(sf[["timestamp_client", "value"]])
            csv = sf[["timestamp_client", "value"]].to_csv().encode('utf-8')
            if st.download_button(
                    label="Click to download table as CSV file.",
                    data=csv,
                    file_name='Wi-Fi strength signal for: ' + gateway_id + '.csv',
                    mime='text/csv',
            ):
                st.session_state["submitted"] = True


            wifi_for_last_3days="Wi-Fi strength signal for last 3 days(in dBm): "
            st.write(wifi_for_last_3days, int(avgsignal))
        else:
            avgsignal=''
        st.subheader("Rest details:")
        st.write("Gateway id: ", str(df["gateway_id"].iloc[0]))
        st.write("Installation id: ", str(df["installation_id"].iloc[0]))
        st.write("Boiler id: ", str(df["boiler_id"].iloc[0]))
        boiler_id = str(df["boiler_id"].iloc[0])
        st.write("Topology hash: ", str(df["topology_hash"].iloc[0]))
        st.write("Your boiler material id: ", str(boiler_id[:7]))
        st.write("Your gateway material id: ", str(gateway_id[:7]))
        link = "https://viguide.viessmann.com/installations/" + str(
            df["installation_id"].iloc[0]) + "?gatewaySerial=" + gateway_id
        st.write("ViGuide:", link)



        report=text+"\n"+text1+"\n"+wifi_for_last_3days+str(avgsignal)
        st.code("---Summary---"+"\n"+"Device with gateway "+gateway_id+" has:\n"+report,)

        # Define your javascript
        my_js = """
        alert("Your data is ready!");
        """

        my_html = f"<script>{my_js}</script>"
        components.html(my_html)


else:
    info = '<span class="row-widget stButton" style="width: 304px;" ><span style="font-size: 24px; color: rgb(97 210 132);" > Please use </span> <button kind="primary" class ="css-1qrvfrg edgvbvh9"> Login!</button></span> <span style="font-size: 24px; color: rgb(97 210 132);" >button in the panel on the left. If you do not see it, press the gray arrowhead in the upper left corner to show the panel. </span>'
    st.markdown(info, unsafe_allow_html=True)